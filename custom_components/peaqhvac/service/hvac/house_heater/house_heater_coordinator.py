from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Tuple

from custom_components.peaqhvac.service.hvac.const import WAITTIMER_TIMEOUT, HEATBOOST_TIMER
from custom_components.peaqhvac.service.hvac.house_heater.temperature_helper import HouseHeaterTemperatureHelper
from custom_components.peaqhvac.service.hvac.interfaces.iheater import IHeater
from custom_components.peaqhvac.service.models.enums.demand import Demand
from custom_components.peaqhvac.service.models.enums.hvacmode import HvacMode
from peaqevcore.common.wait_timer import WaitTimer

_LOGGER = logging.getLogger(__name__)

OFFSET_MIN_VALUE = -10

class HouseHeaterCoordinator(IHeater):
    def __init__(self, hvac):
        self._hvac = hvac
        self._degree_minutes = 0
        self._current_offset: int = 0
        self._wait_timer_breach = WaitTimer(timeout=WAITTIMER_TIMEOUT)
        self._latest_boost = WaitTimer(timeout=HEATBOOST_TIMER)
        self._temp_helper = HouseHeaterTemperatureHelper(hub=hvac.hub)
        super().__init__(hvac=hvac)

    @property
    def is_initialized(self) -> bool:
        return True

    @IHeater.demand.setter
    def demand(self, val):
        self._demand = val

    @property
    def current_offset(self) -> int:
        return self._current_offset

    @current_offset.setter
    def current_offset(self, val) -> None:
        if isinstance(val, (float, int)):
            self._current_offset = val

    @property
    def current_tempdiff(self):
        return self._temp_helper.get_tempdiff_inverted(self.current_offset)

    @property
    def current_temp_extremas(self):
        return self._temp_helper.get_temp_extremas(self.current_offset)

    @property
    def current_temp_trend_offset(self):
        return self._temp_helper.get_temp_trend_offset(self.current_offset)

    def _temporarily_lower_offset(self, input_offset) -> int:
        if self._wait_timer_breach.is_timeout():
            if any(
                [self._lower_offset_threshold_breach(), self._lower_offset_addon()]
            ):
                _LOGGER.debug("Lowering offset -2.")
                input_offset -= 2
        elif self._hvac.hub.sensors.peaqev_installed:
            if self._hvac.hvac_dm <= self._hvac.hub.options.heating_options.low_degree_minutes:
                _LOGGER.debug("Lowering offset -1.")
                input_offset -= 1
        return input_offset

    def get_current_offset(self, offsets: dict) -> Tuple[int, bool]:
        if any([
            self._hvac.hub.sensors.average_temp_outdoors.value > self._hvac.hub.options.heating_options.outdoor_temp_stop_heating,
            self._hvac.hub.offset.max_price_lower(self._hvac.hub.sensors.get_tempdiff())]):
            return OFFSET_MIN_VALUE, True

        _force_update: bool = False
        desired_offset = self._set_calculated_offset(offsets, _force_update)

        if desired_offset <= 0 and self.current_tempdiff <= 0:
            return self._get_lower_offset(), _force_update

        if self._should_adjust_offset(desired_offset):
            return self._adjust_offset(desired_offset), _force_update

        lowered_offset = self._temporarily_lower_offset(desired_offset)
        if lowered_offset < desired_offset:
            desired_offset = lowered_offset
            _force_update = True

        if _force_update:
            self._hvac.hub.observer.broadcast("update operation")
        return self._hvac.hub.offset.adjust_to_threshold(desired_offset), _force_update

    def _get_lower_offset(self) -> int:
        return self._set_lower_offset_strong(
                current_offset=self._current_offset,
                temp_diff=self.current_tempdiff,
                temp_trend=self.current_temp_trend_offset,
            )

    def _should_adjust_offset(self, desired_offset: int) -> bool:
        return (
                self._hvac.hub.offset.model.raw_offsets
                != self._hvac.hub.offset.model.calculated_offsets
                and desired_offset < 0
        )

    def _adjust_offset(self, desired_offset: int) -> int:
        return self._hvac.hub.offset.adjust_to_threshold(desired_offset)

    def _lower_offset_addon(self) -> bool:
        if self._hvac.hvac_electrical_addon > 0:
            _LOGGER.debug("Lowering offset because electrical addon is on.")
            self._wait_timer_breach.update()
            return True
        return False

    def _lower_offset_threshold_breach(self) -> bool:
        if all(
            [
                self._hvac.hub.sensors.peaqev_installed,
                30 <= datetime.now().minute < 58,
                self._hvac.hub.sensors.peaqev_facade.above_stop_threshold
            ]
        ):
            _LOGGER.debug("Lowering offset because of peak about to be breached.")
            self._wait_timer_breach.update()
            return True
        return False

    def _get_demand(self) -> Demand:
        _compressor_start = self._hvac.hvac_compressor_start or -300
        _return_temp = self._hvac.delta_return_temp or 1000
        dm = self._hvac.hvac_dm
        if any([dm is None, _return_temp is None, _compressor_start is None]):
            return Demand.NoDemand
        if dm >= 0 or _return_temp < 0:
            return Demand.NoDemand
        if dm > int(_compressor_start / 2):
            return Demand.LowDemand
        if dm > _compressor_start:
            return Demand.MediumDemand
        if dm <= _compressor_start:
            return Demand.HighDemand
        else:
            _LOGGER.debug(
                f"Compressor_start: {_compressor_start}, delta-return: {self._hvac.delta_return_temp} and pushed DM: {dm}. Could not calculate demand."
            )
            return Demand.NoDemand

    def _set_calculated_offset(self, offsets: dict, _force_update: bool) -> int:
        self._check_next_hour_offset(offsets=offsets, force_update=_force_update)
        ret = sum(
            [
                self.current_offset,
                self.current_tempdiff,
                self.current_temp_extremas,
                self.current_temp_trend_offset,
            ]
        )
        return int(round(ret, 0))

    def _check_next_hour_offset(self, offsets: dict, force_update: bool) -> None:
        hour = datetime.now().replace(minute=0, second=0, microsecond=0)
        if datetime.now().minute >= 40:
            hour += timedelta(hours=1)
        try:
            if self._hvac.hub.price_below_min(hour):
                _offset = max(offsets[hour],0)
            else:
                _offset = offsets[hour]
        except:
            _LOGGER.warning(
                "No Price-offsets have been calculated. Setting base-offset to 0."
            )
            _offset = 0
        if self.current_offset != _offset:
            force_update = True
            self.current_offset = _offset

    def _add_temp_boost(self, pre_offset: int) -> int:
        if not self._latest_boost.is_timeout():
            if self._hvac.hub.sensors.get_tempdiff() > 1:
                pre_offset -= 1
                self._latest_boost.reset()
            return pre_offset

        if not all([
            self._hvac.hvac_mode == HvacMode.Idle,
            self._hvac.hub.sensors.get_tempdiff() < 0,
            self._hvac.hub.sensors.temp_trend_indoors.gradient <= 0.3,
        ]):
            return pre_offset

        _LOGGER.debug("Adding additional heating since there is no sunwarming happening and house is too cold.")
        self._latest_boost.update()
        return pre_offset + 1


    async def async_update_operation(self):
        pass

    @staticmethod
    def _set_lower_offset_strong(current_offset, temp_diff, temp_trend) -> int:
        calc = sum([current_offset, temp_diff, temp_trend])
        ret = max(-5, calc)
        return round(ret, 0)




