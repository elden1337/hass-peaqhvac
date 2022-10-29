import logging
from statistics import mean
from typing import Tuple
import custom_components.peaqhvac.service.hvac.peakfinder as peakfinder

_LOGGER = logging.getLogger(__name__)


class Offset:
    max_hour_today: int = -1
    max_hour_tomorrow: int = -1
    peaks_today: list[int] = []

    prices_today = [1]
    prices_tomorrow = [1]
    calculated_offsets = {}, {}

    @staticmethod
    def getoffset(
            tolerance: int,
            prices: list,
            prices_tomorrow: list
    ) -> Tuple[dict, dict]:
        if any(
                [
                    Offset.prices_today != prices,
                    Offset.prices_tomorrow != prices_tomorrow
                 ]
        ):
            Offset.prices_today = prices
            Offset.prices_tomorrow = prices_tomorrow
            Offset.calculated_offsets = Offset._update_offset(tolerance)

        #_LOGGER.debug(f"Offset not recalculated since prices are not changed.")
        return Offset.calculated_offsets

    @staticmethod
    def _update_offset(tolerance: int) -> Tuple[dict, dict]:
        try:
            average = Offset._getaverage(Offset.prices_today, Offset.prices_tomorrow)
            today = Offset._get_offset_per_day(tolerance, Offset.prices_today, Offset.prices_tomorrow, average)
            tomorrow = Offset._get_offset_per_day(tolerance, Offset.prices_today, Offset.prices_tomorrow, average, is_tomorrow=True)
            return Offset._smooth_transitions(today, tomorrow, tolerance)
        except Exception as e:
            _LOGGER.debug(f"Exception while trying to calculate offset: {e}")
            return {}, {}

    @staticmethod
    def _get_offset_per_day(
            tolerance: int,
            prices: list,
            prices_tomorrow: list,
            average: float,
            is_tomorrow: bool = False
    ) -> dict:
        ret = {}
        try:
            for hour in range(0, 24):
                current_hour = prices[hour] if not is_tomorrow else prices_tomorrow[hour]
                adjustment = (((current_hour/average) - 1) * tolerance) * -1
                ret[hour] = Offset.adjust_to_threshold(adjustment=adjustment, tolerance=tolerance)
        except:
            pass
        return ret

    @staticmethod
    def _smooth_transitions(today: dict, tomorrow: dict, tolerance: int) -> Tuple[dict, dict]:
        tolerance = min(tolerance, 4)
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
        if len(tomorrow.items()) == 24:
            for hour in range(24, 48):
                ret[1][hour - 24] = start_list[hour]
        return ret

    @staticmethod
    def _find_single_anomalies(adj: list) -> list[int]:
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
            if not isinstance(i, float | int):
                return []
        return inputlist

