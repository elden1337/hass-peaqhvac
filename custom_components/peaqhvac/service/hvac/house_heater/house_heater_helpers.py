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
        self._aux_offset_adjustments = {
            OffsetAdjustments.TemporarilyLowerOffset: 0,
            OffsetAdjustments.PeakHour: 0,
            OffsetAdjustments.KeepCompressorRunning: 0,
            OffsetAdjustments.LowerOffsetStrong: 0
        }
    def _get_lower_offset(self, offsetdata: CalculatedOffsetModel) -> int:
        return self._set_lower_offset_strong(
                current_offset=offsetdata.current_offset,
                temp_diff=offsetdata.current_tempdiff,
                temp_trend=offsetdata.current_temp_trend_offset,
                current_outside_temp=self._hvac.hub.sensors.average_temp_outdoors.value
            )

    def _should_adjust_offset(self, offsetdata: CalculatedOffsetModel) -> bool:
        return (
                self._hvac.hub.offset.model.raw_offsets != self._hvac.hub.offset.model.calculated_offsets
                and offsetdata.sum_values() != 0
        )

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

    def _keep_compressor_running(self, offsetdata: CalculatedOffsetModel) -> None:
        """in certain conditions, up the offset to keep the compressor running for energy savings"""
        dm_zero_prediction = self._hvac.hub.sensors.dm_trend.predicted_time_at_value(0)
        now = datetime.now()
        if dm_zero_prediction is not None:
            if all([
                self._hvac.hvac_mode is HvacMode.Heat,
                self._hvac.compressor_frequency > 0,
                self._hvac.hub.sensors.average_temp_outdoors.value < 0,
                dm_zero_prediction < now + timedelta(hours=1)
            ]):
                #_LOGGER.debug(f"adjusting keep compressor running. {offsetdata.current_offset + 1}")
                offsetdata.current_offset += 1
                self._aux_offset_adjustments[OffsetAdjustments.KeepCompressorRunning] = 1
        else:
            self._aux_offset_adjustments[OffsetAdjustments.KeepCompressorRunning] = 0

    def _set_lower_offset_strong(self, current_offset, temp_diff, temp_trend,current_outside_temp) -> int:
        calc = sum([current_offset, temp_diff, temp_trend])
        minval = -5 if current_outside_temp > 5 else -3
        ret = max(minval, calc)
        if ret != current_offset:
            self._aux_offset_adjustments[OffsetAdjustments.LowerOffsetStrong] = ret
        else:
            self._aux_offset_adjustments[OffsetAdjustments.LowerOffsetStrong] = 0
        return round(ret, 0)

    def _helper_get_demand(self) -> Demand:
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

    def _temporarily_lower_offset(self, input_offset) -> int:
        ret = input_offset.current_offset * 1
        if self._wait_timer_breach.is_timeout():
            if any(
                [self._lower_offset_threshold_breach(), self._lower_offset_addon()]
            ):
                self._aux_offset_adjustments[OffsetAdjustments.TemporarilyLowerOffset] = -2
                ret -= 2
        elif self._hvac.hub.sensors.peaqev_installed:
            if self._hvac.hvac_dm <= self._hvac.hub.options.heating_options.low_degree_minutes:
                self._aux_offset_adjustments[OffsetAdjustments.TemporarilyLowerOffset] = -1
                ret -= 1
        else:
            self._aux_offset_adjustments[OffsetAdjustments.TemporarilyLowerOffset] = 0
        if ret != self._temp_lower_offset_num:
            self._temp_lower_offset_num = ret
        return ret