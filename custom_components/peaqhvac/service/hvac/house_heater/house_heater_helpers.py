import logging
from datetime import datetime, timedelta

from peaqevcore.common.wait_timer import WaitTimer
from custom_components.peaqhvac.service.hvac.const import WAITTIMER_TIMEOUT, HEATBOOST_TIMER
from custom_components.peaqhvac.service.hvac.house_heater.models.calculated_offset import CalculatedOffsetModel
from custom_components.peaqhvac.service.hvac.house_heater.models.offset_adjustments import OffsetAdjustments
from custom_components.peaqhvac.service.models.enums.demand import Demand
from custom_components.peaqhvac.service.models.enums.hvacmode import HvacMode

_LOGGER = logging.getLogger(__name__)


class HouseHeaterHelpers:
    def __init__(self, hvac):
        self._hvac = hvac
        self._demand = Demand.NoDemand
        self._temp_lower_offset_num: int = 0
        self._latest_boost = WaitTimer(timeout=HEATBOOST_TIMER)
        self._wait_timer_breach = WaitTimer(timeout=WAITTIMER_TIMEOUT)
        self.aux_offset_adjustments = {
            OffsetAdjustments.TemporarilyLowerOffset: 0,
            OffsetAdjustments.PeakHour: 0,
            OffsetAdjustments.KeepCompressorRunning: 0,
            OffsetAdjustments.LowerOffsetStrong: 0
        }

    def _lower_offset_addon(self) -> bool:
        if self._hvac.hvac_electrical_addon:
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

    def helper_get_demand(self) -> Demand:
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

    def temporarily_lower_offset(self, offsetdata: CalculatedOffsetModel) -> bool:
        if self._wait_timer_breach.is_timeout():
            if any([self._lower_offset_threshold_breach(), self._lower_offset_addon()]):
                net_adjustment = -2
            else:
                net_adjustment = 0
        elif self._hvac.hub.sensors.peaqev_installed:
            if (self._hvac.hvac_dm <= self._hvac.hub.options.heating.low_dm
                    and self._hvac.hub.sensors.average_temp_outdoors.value > -10):
                net_adjustment = -1
            else:
                net_adjustment = 0
        else:
            net_adjustment = 0

        last_adjustment = self.aux_offset_adjustments.get(OffsetAdjustments.TemporarilyLowerOffset, 0)
        adjustment_difference = net_adjustment - last_adjustment
        offsetdata.current_offset += adjustment_difference
        self.aux_offset_adjustments[OffsetAdjustments.TemporarilyLowerOffset] = net_adjustment

        return True
