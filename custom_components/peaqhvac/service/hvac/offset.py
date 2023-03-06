from __future__ import annotations

import logging
from statistics import mean
from typing import Tuple
import custom_components.peaqhvac.service.hvac.peakfinder as peakfinder
from peaqevcore.services.hourselection.hoursselection import Hoursselection
from custom_components.peaqhvac.service.models.offset_model import OffsetModel
from custom_components.peaqhvac.service.models.enums.hvac_presets import HvacPresets

_LOGGER = logging.getLogger(__name__)


class Offset:
    """The class that provides the offsets for the hvac"""

    def __init__(self, hub):
        self._hub = hub
        self.model = OffsetModel(hub)
        self.internal_preset = None
        if not self._hub.sensors.peaqev_installed:
            _LOGGER.debug("initializing an hourselection-instance")
            self.hours = Hoursselection()
        else:
            _LOGGER.debug("found peaqev and will not init hourelection")
            self.hours = None
            self._prices = None
            self._prices_tomorrow = None
            self._offsets = None
        self._hub.observer.add("prices changed", self.update_prices)
        self._hub.observer.add("prognosis changed", self.update_prognosis)
        self._hub.observer.add("hvac preset changed", self.update_preset)

    @property
    def prices(self) -> list:
        if not self._hub.sensors.peaqev_installed:
            return self.hours.prices
        return self._prices

    @property
    def prices_tomorrow(self) -> list:
        if not self._hub.sensors.peaqev_installed:
            return self.hours.prices_tomorrow
        return self._prices_tomorrow

    @property
    def offsets(self) -> dict:
        if not self._hub.sensors.peaqev_installed:
            return self.hours.offsets
        self._offsets = self._hub.sensors.peaqev_facade.offsets
        return self._offsets

    def get_offset(self) -> Tuple[dict, dict]:
        """External entrypoint to the class"""
        if len(self.model.calculated_offsets[0]) == 0:
            _LOGGER.debug("no offsets available. recalculating")
            self._set_offset()
        return self.model.calculated_offsets

    def update_prognosis(self) -> None:
        self.model.prognosis = self._hub.prognosis.prognosis
        self._set_offset()

    def update_prices(self):
        return self._update_prices_internal()
    
    def _update_prices_internal(self) -> None:
        if not self._hub.sensors.peaqev_installed:
            self.hours.prices = self._hub.nordpool.prices
            self.hours.prices_tomorrow = self._hub.nordpool.prices_tomorrow
        else:
            self._prices = self._hub.nordpool.prices
            self._prices_tomorrow = self._hub.nordpool.prices_tomorrow
            if len(self._hub.nordpool.prices) > 24:
                _LOGGER.debug(f"nordpool prices being updated are {len(self._hub.nordpool.prices)} long.")
        self._set_offset()

    def update_preset(self) -> None:
        self.internal_preset = self._hub.sensors.set_temp_indoors.preset
        self._set_offset()

    def _update_offset(self,weather_adjusted_today=None) -> Tuple[dict, dict]:
        try:
            d = self.offsets
            today = self._offset_per_day(d.get('today')) if weather_adjusted_today is None else weather_adjusted_today
            tomorrow = {}
            if len(d.get('tomorrow')):
                tomorrow = self._offset_per_day(d.get('tomorrow'))
            return Offset._smooth_transitions(today, tomorrow, self.model.tolerance)
        except Exception as e:
            _LOGGER.exception(f"Exception while trying to calculate offset: {e}")
            return {}, {}

    def _set_offset(self) -> None:
        if all([
            self.prices is not None,
            self.model.prognosis is not None
        ]):
            if 23 <= len(self.prices) <= 25:
                self.model.raw_offsets = self._update_offset()
            else:
                _LOGGER.debug(f"Prices are not ok. length is {len(self.prices)}")
            try:
                _weather_dict = self._hub.prognosis.get_weatherprognosis_adjustment(self.model.raw_offsets)
                _weather_inverted = {k: v * -1 for (k, v) in _weather_dict[0].items()}
                self.model.calculated_offsets = self._update_offset(_weather_inverted)
            except Exception as e:
                _LOGGER.warning(f"Unable to calculate prognosis-offsets. Setting normal calculation: {e}")
                self.model.calculated_offsets = self.model.raw_offsets
            self._hub.observer.broadcast("offset recalculation")
        else:
            _LOGGER.debug("not possible to calculate offset.")

    def _offset_per_day(self, day_values: dict) -> dict:
        ret = {}
        _max_today = max(day_values.values())
        _min_today = min(day_values.values())
        if self.model.tolerance is not None:
            try:
                factor = max(abs(_max_today), abs(_min_today)) / self.model.tolerance
            except ZeroDivisionError as z:
                _LOGGER.info(f"Offset calculation not finalized due to missing tolerance. Will change shortly...")
                factor = 1
            for k, v in day_values.items():
                ret[k] = int(round((day_values[k] / factor) * -1, 0))
                if self._hub.sensors.set_temp_indoors.preset is HvacPresets.Away:
                    ret[k] -= 1
        return ret

    def adjust_to_threshold(self, adjustment: int) -> int:
        ret = int(round(min(adjustment, self.model.tolerance) if adjustment >= 0 else max(adjustment, self.model.tolerance * -1), 0))
        return ret

    def _getaverage(self, prices: list, prices_tomorrow: list = None) -> float:
        try:
            total = prices
            self.model.peaks_today = peakfinder.identify_peaks(prices) #refactor
            prices_tomorrow_cleaned = Offset._sanitize_pricelists(prices_tomorrow)
            if len(prices_tomorrow_cleaned) == 24:
                total.extend(prices_tomorrow_cleaned)
            return mean(total)
        except Exception as e:
            _LOGGER.exception(f"Could not set offset. prices: {prices}, prices_tomorrow: {prices_tomorrow}. {e}")
            return 0.0

    @staticmethod
    def _sanitize_pricelists(inputlist) -> list:
        if inputlist is None or len(inputlist) < 24:
            return []
        for i in inputlist:
            if not isinstance(i, (float, int)):
                return []
        return inputlist

    @staticmethod
    def _find_single_anomalies(
            adj: list
    ) -> list[int]:
        for idx, p in enumerate(adj):
            if idx <= 1 or idx >= len(adj) - 1:
                pass
            else:
                if all([
                    adj[idx - 1] == adj[idx + 1],
                    adj[idx - 1] != adj[idx]
                ]):
                    _prev = adj[idx - 1]
                    _curr = adj[idx]
                    diff = max(_prev, _curr) - min(_prev, _curr)
                    if int(diff / 2) > 0:
                        if _prev > _curr:
                            adj[idx] += int(diff / 2)
                        else:
                            adj[idx] -= int(diff / 2)
        return adj

    @staticmethod
    def _smooth_transitions(
            today: dict,
            tomorrow: dict,
            tolerance: int
    ) -> Tuple[dict, dict]:
        tolerance = min(tolerance, 3)
        start_list = []
        start_list.extend(today.values())
        start_list.extend(tomorrow.values())

        # Find and remove single anomalies.
        start_list = Offset._find_single_anomalies(start_list)
        # Smooth out transitions upwards so that there is less risk of electrical addon usage.
        for idx, v in enumerate(start_list):
            if idx < len(start_list) - 1:
                if start_list[idx + 1] >= start_list[idx] + tolerance:
                    start_list[idx] += 1
        # Package it and return
        ret = {}, {}
        for hour in range(0, 24):
            ret[0][hour] = start_list[hour]
        if 23 <= len(tomorrow.items()) <= 25:
            for hour in range(24, min(len(tomorrow.items()) + 24, 48)):
                ret[1][hour - 24] = start_list[hour]
        return ret
