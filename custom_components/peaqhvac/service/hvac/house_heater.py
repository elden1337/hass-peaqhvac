from __future__ import annotations
from typing import Tuple

from custom_components.peaqhvac.service.hvac.iheater import IHeater
from custom_components.peaqhvac.service.models.enums.demand import Demand
from datetime import datetime
import logging
import statistics
import time
from custom_components.peaqhvac.service.models.enums.hvacmode import HvacMode

_LOGGER = logging.getLogger(__name__)
HEATBOOST_TIMER = 7200
WAITTIMER_TIMEOUT = 240
LOW_DEGREE_MINUTES = -600


class HouseHeater(IHeater):
    def __init__(self, hvac):
        self._hvac = hvac
        self._dm_compressor_start = hvac.hvac_compressor_start
        self._latest_boost = 0
        self._degree_minutes = 0
        self._current_vent_state: bool = False
        self._current_offset = 0
        self._wait_timer_boost = 0
        self._wait_timer_breach = 0
        super().__init__(hvac=hvac)
        #self._hvac.hub.sensors.peaqev_facade.add_callback("", self._update_degree_minutes)

    @property
    def is_initialized(self) -> bool:
        return True

    @IHeater.demand.setter
    def demand(self, val):
        self._demand = val

    @property
    def vent_boost(self) -> bool:
        return self._should_vent_boost()

    @property
    def current_offset(self) -> int:
        return self._current_offset

    @current_offset.setter
    def current_offset(self, val) -> None:
        if isinstance(val, (float, int)):
            self._current_offset = val

    @property
    def current_tempdiff(self):
        return self._get_tempdiff_inverted()

    @property
    def current_temp_extremas(self):
        return self._get_temp_extremas()

    @property
    def current_temp_trend_offset(self):
        return self._get_temp_trend_offset()

    def _temporarily_lower_offset(self, input_offset) -> int:
        if time.time() - self._wait_timer_breach > WAITTIMER_TIMEOUT:
            if any([
                self._lower_offset_threshold_breach(),
                self._temp_lower_offset_addon()
            ]):
                _LOGGER.debug("Lowering offset -2.")
                input_offset -= 2
        elif self._hvac.hub.sensors.peaqev_installed:
            if self._hvac.hvac_dm <= LOW_DEGREE_MINUTES:
                _LOGGER.debug("Lowering offset -1.")
                input_offset -= 1
        return input_offset

    def get_current_offset(self, offsets: dict) -> Tuple[int, bool]:
        if self._hvac.hub.offset.max_price_lower(self._get_tempdiff()):
            return -10, True
        desired_offset = self._set_calculated_offset(offsets)
        _force_update: bool = False
        if desired_offset <= 0 and self.current_tempdiff <= 0:
            return self._set_lower_offset_strong(
                current_offset=self._current_offset,
                temp_diff=self.current_tempdiff,
                temp_trend=self._get_temp_trend_offset()
            ), _force_update

        if self._hvac.hub.offset.model.raw_offsets != self._hvac.hub.offset.model.calculated_offsets and desired_offset < 0:
            return self._hvac.hub.offset.adjust_to_threshold(desired_offset), _force_update
        lowered_offset = self._temporarily_lower_offset(desired_offset)
        if lowered_offset < desired_offset:
            desired_offset = lowered_offset
            _force_update = True
        return self._hvac.hub.offset.adjust_to_threshold(desired_offset), _force_update

    def _temp_lower_offset_addon(self) -> bool:
        if self._hvac.hvac_electrical_addon > 0:
            _LOGGER.debug("Lowering offset because electrical addon is on.")
            self._wait_timer_breach = time.time()
            return True
        return False

    def _lower_offset_threshold_breach(self) -> bool:
        if all([
            self._hvac.hub.sensors.peaqev_installed,
            30 <= datetime.now().minute < 58,
            float(self._hvac.hub.sensors.peaqev_facade.exact_threshold) >= 100
        ]):
            _LOGGER.debug("Lowering offset because of peak about to be breached.")
            self._wait_timer_breach = time.time()
            return True
        return False

    def _get_demand(self) -> Demand:
        _compressor_start = self._dm_compressor_start if self._dm_compressor_start is not None else -300
        _return_temp = self._hvac.delta_return_temp if self._hvac.delta_return_temp is not None else 1000
        dm = self._hvac.hvac_dm
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
                f"Compressor_start: {_compressor_start}, delta-return: {self._hvac.delta_return_temp} and pushed DM: {dm}. Could not calculate demand.")
            return Demand.NoDemand

    def _set_calculated_offset(self, offsets: dict) -> int:
        self._update_current_offset(offsets=offsets)
        ret = sum([
            self.current_offset,
            self.current_tempdiff,
            self._get_temp_extremas(),
            self._get_temp_trend_offset()
        ])
        return int(round(ret, 0))

    def _update_current_offset(self, offsets: dict) -> None:
        hour = datetime.now().hour
        if datetime.now().hour < 23 and datetime.now().minute >= 50:
            hour = datetime.now().hour + 1
        try:
            _offset = offsets[hour]
        except:
            _LOGGER.warning("No Price-offsets have been calculated. Setting base-offset to 0.")
            _offset = 0
        self.current_offset = _offset

    def _add_temp_boost(self, pre_offset: int) -> int:
        if time.time() - self._latest_boost > HEATBOOST_TIMER:
            if all([
                self._hvac.hvac_mode == HvacMode.Idle,
                self._get_tempdiff() < 0,
                self._hvac.hub.sensors.temp_trend_indoors.gradient <= 0.3
            ]):
                _LOGGER.debug("adding additional heating since there is no sunwarming happening and house is too cold.")
                pre_offset += 1
                self._latest_boost = time.time()
        else:
            pre_offset += 1
            if self._get_tempdiff() > 1:
                pre_offset -= 1
                self._latest_boost = 0
        return pre_offset

    def _get_tempdiff_inverted(self) -> int:
        diff = self._get_tempdiff()
        if diff == 0:
            return 0
        _tolerance = self._determine_tolerance(diff)
        return int(diff / _tolerance) * -1

    def _get_tempdiff(self) -> float:
        _indoors = self._hvac.hub.sensors.average_temp_indoors.value
        _set_temp = self._hvac.hub.sensors.set_temp_indoors.adjusted_temp
        return _indoors - _set_temp

    def _get_temp_extremas(self) -> float:
        _diffs = [], []
        set_temp = self._hvac.hub.sensors.set_temp_indoors.adjusted_temp
        for t in self._hvac.hub.sensors.average_temp_indoors.all_values:
            _diff = set_temp - t
            if _diff > 0:
                _diffs[0].append(_diff)
            elif _diff < 0:
                _diffs[1].append(_diff)
        if len(_diffs[0]) == len(_diffs[1]):
            return 0
        _cold = len(_diffs[0]) > len(_diffs[1])
        _tolerance = self._determine_tolerance(_cold)
        if len(_diffs[0]) > len(_diffs[1]):
            ret = statistics.mean(_diffs[0]) - _tolerance
        else:
            ret = statistics.mean(_diffs[1]) + _tolerance
        return round(ret, 2)

    def _get_temp_trend_offset(self) -> float:
        if self._hvac.hub.sensors.temp_trend_indoors.is_clean:
            if -0.1 < self._hvac.hub.sensors.temp_trend_indoors.gradient < 0.1:
                return 0
            new_temp_diff = self._hvac.hub.predicted_temp - self._hvac.hub.sensors.set_temp_indoors.adjusted_temp
            _tolerance = self._determine_tolerance(new_temp_diff)
            if abs(new_temp_diff) >= _tolerance:
                ret = self._get_offset_steps(_tolerance)
                if new_temp_diff > 0:
                    ret = ret * -1
                if ret == 0:
                    return 0
                return ret
        return 0

    def _get_offset_steps(self, tolerance) -> int:
        ret = abs(self._hvac.hub.sensors.temp_trend_indoors.gradient) / tolerance
        return int(ret)

    def _determine_tolerance(self, determinator) -> float:
        tolerances = self._hvac.hub.sensors.set_temp_indoors.adjusted_tolerances(self._current_offset)
        return tolerances[1] if (determinator > 0 or determinator is True) else tolerances[0]

    def update_operation(self):
        pass

    def _should_vent_boost(self) -> bool:
        if self._hvac.fan_speed < 100:
            if all([
                self._hvac.hub.sensors.temp_trend_indoors.is_clean,
                time.time() - self._wait_timer_boost > WAITTIMER_TIMEOUT
            ]):
                if all([
                    self._get_tempdiff() > 1,
                    self._hvac.hub.sensors.temp_trend_indoors.gradient > 0.5,
                    self._hvac.hub.sensors.temp_trend_outdoors.gradient > 0,
                    self._hvac.hub.sensors.average_temp_outdoors.value >= 0,
                ]):
                    self._vent_boost_start("Vent boosting because of warmth.")
                elif all([
                    self._hvac.hvac_dm <= LOW_DEGREE_MINUTES,
                    self._hvac.hub.sensors.average_temp_outdoors.value >= -12,
                ]):
                    self._vent_boost_start("Vent boosting because of low degree minutes.")
                else:
                    self._current_vent_state = False
        elif any(
            [
                self._hvac.hvac_dm > LOW_DEGREE_MINUTES+100,
                self._hvac.hub.sensors.average_temp_outdoors.value < -12,
            ]
        ):
            """stop vent boosting"""
            self._current_vent_state = False
        return self._current_vent_state

    def _vent_boost_start(self, msg) -> None:
        _LOGGER.debug(msg)
        self._wait_timer_boost = time.time()
        self._current_vent_state = True

    @staticmethod
    def _set_lower_offset_strong(current_offset, temp_diff, temp_trend) -> int:
        calc = sum([current_offset, temp_diff, temp_trend])
        ret = max(-5, calc)
        return round(ret, 0)
