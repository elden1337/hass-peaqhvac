from datetime import datetime
import logging

_LOGGER = logging.getLogger(__name__)


class Offset:

    @staticmethod
    def getoffset(
            tolerance: int,
            prices: list,
            prices_tomorrow: list,
            hour: int = datetime.now().hour
    ) -> int:
        try:
            current_hour = prices[hour]
            adjustment = ((current_hour / Offset._getaverage(prices, prices_tomorrow)) - 1) * -1 * tolerance
            return int(min(adjustment, tolerance) if adjustment > 0 else max(adjustment, tolerance * -1))
        except:
            return 0

    @staticmethod
    def _getaverage(prices: list, prices_tomorrow: list = None) -> float:
        try:
            total = prices
            prices_tomorrow_cleaned = Offset._sanitize_pricelists(prices_tomorrow)
            if len(prices_tomorrow_cleaned) == 24:
                total.extend(prices_tomorrow_cleaned)
            return sum(total) / len(total)
        except Exception as e:
            _LOGGER.exception(f"Could not set offset. prices: {prices}, prices_tomorrow: {prices_tomorrow}. {e}")
            return 0.0

    @staticmethod
    def _sanitize_pricelists(inputlist) -> list:
        if len(inputlist) < 24:
            return []
        for i in inputlist:
            if not isinstance(i, float|int):
                return []
        return inputlist

    #def calc with trend temp
    #def calc with prognosis
    #def calc with current outside vs set temp