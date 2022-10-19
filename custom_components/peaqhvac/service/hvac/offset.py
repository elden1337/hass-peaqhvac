import logging
from statistics import mean
from typing import Tuple

_LOGGER = logging.getLogger(__name__)


class Offset:
    max_hour_today: int = -1
    max_hour_tomorrow: int = -1

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
            return today, tomorrow
        except:
            return {}, {}

    @staticmethod
    def _get_offset_per_day(
            tolerance: int,
            prices: list,
            prices_tomorrow: list,
            average: float,
            is_tomorrow: bool = False
    ):
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
    def adjust_to_threshold(adjustment: int, tolerance: int) -> int:
        return int(round(min(adjustment, tolerance) if adjustment >= 0 else max(adjustment, tolerance * -1), 0))

    @staticmethod
    def _getaverage(prices: list, prices_tomorrow: list = None) -> float:
        try:
            total = prices
            Offset.max_hour_today = prices.index(max(prices))
            prices_tomorrow_cleaned = Offset._sanitize_pricelists(prices_tomorrow)
            if len(prices_tomorrow_cleaned) == 24:
                total.extend(prices_tomorrow_cleaned)
                Offset.max_hour_tomorrow = prices_tomorrow_cleaned.index(max(prices_tomorrow_cleaned))
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

