from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Tuple

from peaqevcore.common.models.observer_types import ObserverTypes

from custom_components.peaqhvac.service.hvac.const import WAITTIMER_TIMEOUT, HEATBOOST_TIMER
from custom_components.peaqhvac.service.hvac.house_heater.models.calculated_offset import CalculatedOffsetModel
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
        self._temp_lower_offset_num: int = 0
        self._offsets: dict = {}
        self._current_adjusted_offset: int = 0
        self._wait_timer_breach = WaitTimer(timeout=WAITTIMER_TIMEOUT)
        self._latest_boost = WaitTimer(timeout=HEATBOOST_TIMER)
        self._temp_helper = HouseHeaterTemperatureHelper(hub=hvac.hub)
        super().__init__(hvac=hvac)

    @property
    def current_adjusted_offset(self) -> int:
        return int(self._current_adjusted_offset)

    @current_adjusted_offset.setter
    def current_adjusted_offset(self, val) -> None:
        if isinstance(val, (float, int)):
            self._current_adjusted_offset = val

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

    def _temporarily_lower_offset(self, input_offset) -> int:
        ret = input_offset.current_offset * 1
        if self._wait_timer_breach.is_timeout():
            if any(
                [self._lower_offset_threshold_breach(), self._lower_offset_addon()]
            ):
                ret -= 2
        elif self._hvac.hub.sensors.peaqev_installed:
            if self._hvac.hvac_dm <= self._hvac.hub.options.heating_options.low_degree_minutes:
                ret -= 1
        if ret != self._temp_lower_offset_num:
            self._temp_lower_offset_num = ret
            if ret != input_offset.current_offset * 1:
                _LOGGER.debug(f"Lowering offset {ret}.")
        return ret

    def get_current_offset(self) -> Tuple[int, bool]:
        # Get the current offsets and store them in an instance variable
        self._offsets = self._hvac.model.current_offset_dict_combined

        # Initialize a flag to indicate whether an update is needed
        _force_update: bool = False

        # Check if the outdoor temperature is above the threshold for stopping heating,
        # or if the maximum price is lower than the temperature difference.
        # If either condition is met and the outdoor temperature is non-negative,
        # return the minimum offset value and a flag indicating that an update is needed.
        outdoor_temp = self._hvac.hub.sensors.average_temp_outdoors.value
        temp_diff = self._hvac.hub.sensors.get_tempdiff()
        stop_heating_temp = self._hvac.hub.options.heating_options.outdoor_temp_stop_heating
        if (outdoor_temp > stop_heating_temp or
            self._hvac.hub.offset.max_price_lower(temp_diff)) and outdoor_temp >= 0:
            return OFFSET_MIN_VALUE, True

        # Get the calculated offset data and update the current offset to keep the compressor running
        offsetdata = self.get_calculated_offsetdata(_force_update)
        offsetdata.current_offset = self.keep_compressor_running(offsetdata.current_offset)

        # If the sum of the offset values and the current temperature difference are both non-positive,
        # get the lower offset, update the current adjusted offset, and return it along with the update flag
        if offsetdata.sum_values() <= 0 and self.current_tempdiff <= 0:
            ret = self._get_lower_offset()
            self.current_adjusted_offset = ret
            return int(ret), _force_update

        # If the offset should be adjusted, adjust it, update the current adjusted offset,
        # and return it along with the update flag
        if self._should_adjust_offset(offsetdata):
            ret = self._adjust_offset(offsetdata)
            self.current_adjusted_offset = ret
            return int(ret), _force_update

        # Temporarily lower the offset if necessary and update the update flag
        lowered_offset = self._temporarily_lower_offset(offsetdata)
        if lowered_offset < offsetdata.sum_values():
            offsetdata.current_offset = lowered_offset
            _force_update = True

        # If an update is needed, broadcast an update operation
        if _force_update:
            self._hvac.hub.observer.broadcast(ObserverTypes.UpdateOperation)

        # Adjust the offset to the threshold, update the current adjusted offset,
        # and return it along with the update flag
        ret = self._hvac.hub.offset.adjust_to_threshold(offsetdata)
        self.current_adjusted_offset = int(ret)
        return self.current_adjusted_offset, _force_update

    def _get_lower_offset(self) -> int:
        return self._set_lower_offset_strong(
                current_offset=self._current_offset,
                temp_diff=self._temp_helper.get_tempdiff_inverted(self.current_offset),
                temp_trend=self._temp_helper.get_temp_trend_offset(),
                current_outside_temp=self._hvac.hub.sensors.average_temp_outdoors.value
            )

    def _should_adjust_offset(self, offsetdata: CalculatedOffsetModel) -> bool:
        return (
                self._hvac.hub.offset.model.raw_offsets
                != self._hvac.hub.offset.model.calculated_offsets
                and offsetdata.sum_values() < 0
        )

    def _adjust_offset(self, offsetdata: CalculatedOffsetModel) -> int:
        return self._hvac.hub.offset.adjust_to_threshold(offsetdata)

    def _lower_offset_addon(self) -> bool:
        if self._hvac.hvac_electrical_addon > 0:
            _LOGGER.debug("Lowering offset because electrical addon is on.")
            self._wait_timer_breach.update()
            return True
        return False

    def _lower_offset_threshold_breach(self) -> bool:
        if self._hvac.hub.sensors.peaqev_installed:
            if all(
                [
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
            return Demand.ErrorDemand

    def get_calculated_offsetdata(self, _force_update: bool = False) -> CalculatedOffsetModel:
        self._check_next_hour_offset(force_update=_force_update)
        return CalculatedOffsetModel(self.current_offset,
                                     self._temp_helper.get_tempdiff_inverted(self.current_offset),
                                     self._temp_helper.get_temp_extremas(self.current_offset),
                                     self._temp_helper.get_temp_trend_offset())

    def _check_next_hour_offset(self, force_update: bool) -> None:
        if not len(self._offsets):
            return
        hour = datetime.now().replace(minute=0, second=0, microsecond=0)
        if datetime.now().minute >= 40:
            hour += timedelta(hours=1)
        try:
            if self._hvac.hub.price_below_min(hour):
                _offset = max(self._offsets[hour],0)
            else:
                _offset = self._offsets[hour]
        except:
            _LOGGER.warning(
                "No Price-offsets have been calculated. Setting base-offset to 0."
            )
            _offset = 0
        if self.current_offset != _offset:
            force_update = True
            self.current_offset = _offset

    def keep_compressor_running(self, input_offset) -> int:
        """in certain conditions, up the offset to keep the compressor running for energy savings"""
        dm_prediction = self._hvac.hub.sensors.dm_trend.predicted_time_at_value(0)
        now = datetime.now()
        if any([
            self._hvac.hvac_mode is not HvacMode.Heat,
            self._hvac.hub.sensors.average_temp_outdoors.value >= 0,
            dm_prediction is None,
            dm_prediction > now + timedelta(hours=1)
        ]):
            return input_offset
        return input_offset + 1

    def _add_temp_boost(self, pre_offset: int) -> int:
        #todo: is this one really needed?
        if not self._latest_boost.is_timeout():
            if self._hvac.hub.sensors.get_tempdiff() > 1:
                pre_offset -= 1
                self._latest_boost.reset()
            return pre_offset
        if not all([
            self._hvac.hvac_mode == HvacMode.Idle,
            self._hvac.hub.sensors.get_tempdiff() < 0,
            self._hvac.hub.sensors.temp_trend_indoors.trend <= 0.3,
        ]):
            return pre_offset
        _LOGGER.debug("Adding additional heating since there is no sunwarming happening and house is too cold.")
        self._latest_boost.update()
        return pre_offset + 1

    async def async_update_operation(self):
        pass

    @staticmethod
    def _set_lower_offset_strong(current_offset, temp_diff, temp_trend,current_outside_temp) -> int:
        calc = sum([current_offset, temp_diff, temp_trend])
        minval = -5 if current_outside_temp > 5 else -3
        ret = max(minval, calc)
        return round(ret, 0)




