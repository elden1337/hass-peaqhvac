from __future__ import annotations

import logging
from statistics import mean
from typing import Tuple
import custom_components.peaqhvac.service.hvac.peakfinder as peakfinder
from peaqevcore.services.hourselection.hoursselection import Hoursselection
from datetime import timedelta, datetime
from custom_components.peaqhvac.service.hub.weather_prognosis import PrognosisExportModel
_LOGGER = logging.getLogger(__name__)


class Offset:
    """The class that provides the offsets for the hvac"""
    max_hour_today: int = -1
    max_hour_tomorrow: int = -1
    peaks_today: list[int] = []
    calculated_offsets = {}, {}
    raw_offsets = {}, {}
    _internal_tolerance = 0

    def __init__(self, hub):
        self.hours = Hoursselection()
        self._hub = hub

    def _get_two_hour_prog(self, thishour: datetime) -> PrognosisExportModel | None:
        for p in self._hub.prognosis.prognosis:
            c = timedelta.total_seconds(p.DT - thishour)
            if c == 7200:
                return p
        return None

    def _get_weatherprognosis_adjustment(self, offsets) -> Tuple[dict, dict]:
        # temp fix
        if len(self._hub.prognosis.prognosis) == 0:
            _LOGGER.debug("Prognosis length was 0. updating")
            self._hub.prognosis.update_weather_prognosis()
            self._hub.prognosis.get_hvac_prognosis(self._hub.sensors.average_temp_outdoors.value)
        # temp fix

        for k, v in offsets[0].items():
            now = datetime.now()
            thishour = datetime(now.year, now.month, now.day, int(k), 0, 0)
            prog = self._get_two_hour_prog(thishour)
            if prog is not None:
                adj = int(round(prog.corrected_temp / 2 / 2.5, 0) * -1)
                if adj != v:
                    _LOGGER.debug(f"adjusted {k} from {v} to {adj}")
                    offsets[0][k] = adj
        return offsets[0], offsets[1]

    def getoffset(
            self,
            prices: list,
            prices_tomorrow: list
    ) -> Tuple[dict, dict]:
        """External entrypoint to the class"""
        if any(
                [
                    self.hours.prices != prices,
                    self.hours.prices_tomorrow != prices_tomorrow,
                    self.calculated_offsets == {}, {},
                    self._hub.options.hvac_tolerance != self._internal_tolerance
                ]
        ):
            self.hours.prices = prices
            self.hours.prices_tomorrow = prices_tomorrow
            self._internal_tolerance = self._hub.options.hvac_tolerance
            if 23 <= len(prices) <= 25:
                self.raw_offsets = self._update_offset()
            else:
                _LOGGER.error(f"The pricelist for today was not between 23 and 25 hours long. Cannot calculate offsets. length: {len(prices)}")
            try:
                self.calculated_offsets = self._get_weatherprognosis_adjustment(self.raw_offsets)
            except Exception as e:
                _LOGGER.debug(f"Got to except: {e}")
                self.calculated_offsets = self.raw_offsets
            return self.calculated_offsets

    def _update_offset(self) -> Tuple[dict, dict]:
        try:
            d = self.hours.offsets
            today = self._offset_per_day(d['today'])
            tomorrow = {}
            if len(d['tomorrow']) > 0:
                tomorrow = self._offset_per_day(d['tomorrow'])
            return self._smooth_transitions(today, tomorrow, self._internal_tolerance)
        except Exception as e:
            _LOGGER.exception(f"Exception while trying to calculate offset: {e}")
            return {}, {}

    def _offset_per_day(self, day_values: dict) -> dict:
        ret = {}
        _max_today = max(day_values.values())
        _min_today = min(day_values.values())
        factor = max(abs(_max_today), abs(_min_today)) / self._internal_tolerance

        for k, v in day_values.items():
            ret[k] = int(round((day_values[k] / factor) * -1, 0))
        return ret

    def _smooth_transitions(self, today: dict, tomorrow: dict, tolerance: int) -> Tuple[dict, dict]:
        tolerance = min(tolerance, 4)
        start_list = []
        start_list.extend(today.values())
        start_list.extend(tomorrow.values())

        # Find and remove single anomalies.
        start_list = self._find_single_anomalies(start_list)

        # Smooth out transitions upwards so that there is less risk of electrical addon usage.
        for idx, v in enumerate(start_list):
            if idx < len(start_list) - 1:
                if start_list[idx + 1] >= start_list[idx] + tolerance:
                    start_list[idx] += 1

        # Package it and return
        ret = {}, {}
        for hour in range(0, 24):
            ret[0][hour] = start_list[hour]
        if len(tomorrow.items()) == 24:
            for hour in range(24, 48):
                ret[1][hour - 24] = start_list[hour]
        return ret

    def _find_single_anomalies(self, adj: list) -> list[int]:
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
    def adjust_to_threshold(adjustment: int, tolerance: int) -> int:
        return int(round(min(adjustment, tolerance) if adjustment >= 0 else max(adjustment, tolerance * -1), 0))

    @staticmethod
    def _getaverage(prices: list, prices_tomorrow: list = None) -> float:
        try:
            total = prices
            Offset.peaks_today = peakfinder.identify_peaks(prices)
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
