import logging
from statistics import mean
from typing import Tuple
import custom_components.peaqhvac.service.hvac.peakfinder as peakfinder

_LOGGER = logging.getLogger(__name__)


class Offset:
    max_hour_today: int = -1
    max_hour_tomorrow: int = -1
    peaks_today: list[int] = []

    @staticmethod
    def getoffset(
            tolerance: int,
            prices: list,
            prices_tomorrow: list
    ) -> Tuple[dict, dict]:
        try:
            average = Offset._getaverage(prices, prices_tomorrow)
            today = Offset._get_offset_per_day(tolerance, prices, prices_tomorrow, average)
            tomorrow = Offset._get_offset_per_day(tolerance, prices, prices_tomorrow, average, is_tomorrow=True)
            return Offset._smooth_transitions(today, tomorrow, tolerance)
        except:
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
                adjustment_capped = Offset.adjust_to_threshold(adjustment=adjustment, tolerance=tolerance)
                ret[hour] = adjustment_capped
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
        ret1 = {}
        ret2 = {}
        for hour in range(0, 24):
            ret1[hour] = start_list[hour]
        if len(tomorrow.items()) == 24:
            for hour in range(24, 48):
                ret2[hour - 24] = start_list[hour]
        return ret1, ret2

    @staticmethod
    def _find_single_anomalies(adjustments: list) -> list[int]:
        for idx, p in enumerate(adjustments):
            if idx <= 1 or idx >= len(adjustments) - 1:
                pass
            else:
                if all([
                    adjustments[idx - 1] == adjustments[idx + 1],
                    adjustments[idx - 1] != adjustments[idx]
                ]):
                    _prev = adjustments[idx - 1]
                    _curr = adjustments[idx]
                    diff = max(_prev, _curr) - min(_prev, _curr)
                    if int(diff / 2) > 0:
                        if _prev > _curr:
                            adjustments[idx] += int(diff / 2)
                        else:
                            adjustments[idx] -= int(diff / 2)
        return adjustments

    @staticmethod
    def adjust_to_threshold(adjustment: int, tolerance: int) -> int:
        return int(round(min(adjustment, tolerance) if adjustment >= 0 else max(adjustment, tolerance * -1), 0))

    @staticmethod
    def _getaverage(prices: list, prices_tomorrow: list = None) -> float:
        try:
            total = prices
            #Offset.max_hour_today = prices.index(max(prices))
            Offset.peaks_today = peakfinder.identify_peaks(prices)
            prices_tomorrow_cleaned = Offset._sanitize_pricelists(prices_tomorrow)
            if len(prices_tomorrow_cleaned) == 24:
                total.extend(prices_tomorrow_cleaned)
                #Offset.max_hour_tomorrow = prices_tomorrow_cleaned.index(max(prices_tomorrow_cleaned))
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

