from __future__ import annotations

from custom_components.peaqhvac.service.hvac.iheater import IHeater
from custom_components.peaqhvac.service.models.enums.demand import Demand
from custom_components.peaqhvac.service.hvac.offset import Offset
from datetime import datetime
import logging
import statistics as stat
import time

from custom_components.peaqhvac.service.models.enums.hvacmode import HvacMode

_LOGGER = logging.getLogger(__name__)
HEATBOOST_TIMER = 7200
WAITTIMER_TIMEOUT = 300

class HouseHeater(IHeater):

    def __init__(self, hvac):
        self._hvac = hvac
        self._dm_compressor_start = hvac.hvac_compressor_start
        self._latest_boost = 0
        self._degree_minutes = 0
        self._current_offset = 0
        self._wait_timer = 0
        super().__init__(hvac=hvac)

    @property
    def is_initialized(self) -> bool:
        return True

    @IHeater.demand.setter
    def demand(self, val):
        self._demand = val

    @property
    def vent_boost(self) -> bool:
        if self._hvac.hub.sensors.temp_trend_indoors.is_clean and time.time() - self._wait_timer > WAITTIMER_TIMEOUT:
            if all(
                    [
                        self._get_tempdiff() > 1,
                        self._hvac.hub.sensors.temp_trend_indoors.gradient > 0.5,
                        self._hvac.hub.sensors.temp_trend_outdoors.gradient > 0,
                        self._hvac.hub.sensors.average_temp_outdoors.value >= -5,
                    ]
            ):
                _LOGGER.debug("Preparing to run ventilation-boost based on hot and current temperature rising.")
                self._wait_timer = time.time()
                return True
            if all([
                self._hvac.hvac_dm <= -700,
                self._hvac.hub.sensors.average_temp_outdoors.value >= -12
            ]):
                _LOGGER.debug("Preparing to run ventilation-boost based on low degree minutes.")
                self._wait_timer = time.time()
                return True
        return False

    @property
    def current_offset(self) -> int:
        return self._current_offset

    @current_offset.setter
    def current_offset(self, val) -> None:
        if isinstance(val, (float,int)):
            self._current_offset = val

    @property
    def current_tempdiff(self):
        return self._get_tempdiff_rounded()

    @property
    def current_temp_extremas(self):
        return self._get_temp_extremas()

    @property
    def current_temp_trend_offset(self):
        return self._get_temp_trend_offset()

    @property
    def dm_lower(self) -> bool:
        if self._hvac.hub.sensors.peaqev_installed:
            if self._hvac.hvac_dm <= -700:
                _LOGGER.debug("Lowering offset low degree minutes.")
                return True
        return False

    @property
    def addon_or_peak_lower(self) -> bool:
        if self._hvac.hub.sensors.peaqev_installed:
            if all([
                30 <= datetime.now().minute < 58,
                float(self._hvac.hub.sensors.peaqev_facade.exact_threshold) >= 100
            ]):
                _LOGGER.debug("Lowering offset because of peak about to be breached.")
                return True
            elif self._hvac.hvac_electrical_addon > 0:
                _LOGGER.debug("Lowering offset because electrical addon is on.")
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

    def get_current_offset(self, offsets: dict) -> int:
        if self.max_price_lower():
            return -10
        else:
            desired_offset = self._set_calculated_offset(offsets)
        if self._hvac.hub.offset.model.raw_offsets != self._hvac.hub.offset.model.calculated_offsets and desired_offset < 0:
            # weather has played it's part, return lower if prognosis tells us to.
            return Offset.adjust_to_threshold(desired_offset, self._hvac.hub.options.hvac_tolerance)
        if self.dm_lower:
            desired_offset -= 1
        if self.addon_or_peak_lower:
            desired_offset -= 2
        elif all([self._current_offset < 0, self._get_tempdiff_rounded() < 0]):
            return round(
                max(-5, sum([self._current_offset, self._get_tempdiff_rounded(), self._get_temp_trend_offset()])), 0)
        return Offset.adjust_to_threshold(desired_offset, self._hvac.hub.options.hvac_tolerance)

    def _set_calculated_offset(self, offsets: dict) -> int:
        hour = datetime.now().hour
        if datetime.now().hour < 23 and datetime.now().minute >= 50:
            hour = datetime.now().hour + 1
        try:
            _offset = offsets[hour]
        except:
            _LOGGER.warning("No Price-offsets have been calculated. Setting base-offset to 0.")
            _offset = 0

        self.current_offset = _offset
        _tempdiff = self._get_tempdiff_rounded()
        _tempextremas = self._get_temp_extremas()
        _temptrend = self._get_temp_trend_offset()

        ret = sum(
            [
                self.current_offset,
                _tempdiff,
                _tempextremas,
                _temptrend
            ]
        )

        return int(round(ret, 0))

    def _add_temp_boost(self, pre_offset: int) -> int:
        if time.time() - self._latest_boost > HEATBOOST_TIMER:
            if all([
                self._hvac.hvac_mode == HvacMode.Idle,
                self._get_tempdiff() < 0,
                self._hvac.hub.sensors.temp_trend_indoors.gradient <= 0.3
            ]):
                """boost +1 since there is no sunwarming and no heating atm"""
                _LOGGER.debug("adding additional heating since there is no sunwarming happening and house is too cold.")
                pre_offset += 1
                self._latest_boost = time.time()
        else:
            pre_offset += 1
            if self._get_tempdiff() > 1:
                """Turn off the boost prematurely"""
                pre_offset -= 1
                self._latest_boost = 0
        return pre_offset

    def max_price_lower(self) -> bool:
        """Temporarily lower to -10 if this hour is a peak for today and temp > set-temp + 0.5C"""
        if self._get_tempdiff() >= 0:
            return datetime.now().hour in self._hvac.hub.offset.model.peaks_today
        return False

    def _get_tempdiff_rounded(self) -> int:
        diff = self._get_tempdiff()
        if diff == 0:
            return 0
        _tolerance = self._determine_tolerance(diff)
        return int(diff / _tolerance) * -1

    def _get_tempdiff(self) -> float:
        return self._hvac.hub.sensors.average_temp_indoors.value - self._hvac.hub.sensors.set_temp_indoors.adjusted_set_temp(self._hvac.hub.sensors.average_temp_indoors.value)

    def _get_temp_extremas(self) -> float:
        low_diffs = []
        high_diffs = []
        set_temp = self._hvac.hub.sensors.set_temp_indoors.adjusted_set_temp(self._hvac.hub.sensors.average_temp_indoors.value)
        for t in self._hvac.hub.sensors.average_temp_indoors.all_values:
            _diff = set_temp - t
            if _diff > 0:
                low_diffs.append(_diff)
            elif _diff < 0:
                high_diffs.append(_diff)
        if len(low_diffs) == len(high_diffs):
            return 0
        _tolerance = self._determine_tolerance(len(low_diffs) > len(high_diffs))
        if len(low_diffs) > len(high_diffs):
            return round(stat.mean(low_diffs) - _tolerance, 2)
        else:
            return round(stat.mean(high_diffs) + _tolerance, 2)

    def _get_temp_trend_offset(self) -> float:
        if self._hvac.hub.sensors.temp_trend_indoors.is_clean:
            if -0.1 < self._hvac.hub.sensors.temp_trend_indoors.gradient < 0.1:
                return 0
            predicted_temp = self._hvac.hub.sensors.average_temp_indoors.value + self._hvac.hub.sensors.temp_trend_indoors.gradient
            new_temp_diff = predicted_temp - self._hvac.hub.sensors.set_temp_indoors.adjusted_set_temp(self._hvac.hub.sensors.average_temp_indoors.value)
            _tolerance = self._determine_tolerance(new_temp_diff)
            if abs(new_temp_diff) >= _tolerance:
                steps = abs(self._hvac.hub.sensors.temp_trend_indoors.gradient) / _tolerance
                ret = int(steps)
                if new_temp_diff > 0:
                    ret = ret * -1
                if ret == 0:
                    return 0
                return ret
        return 0

    def _determine_tolerance(self, determinator) -> float:
        tolerances = self._hvac.hub.sensors.set_temp_indoors.adjusted_tolerances(self._current_offset)
        return tolerances[1] if (determinator > 0 or determinator is True) else tolerances[0]

    # def compare to water demand

