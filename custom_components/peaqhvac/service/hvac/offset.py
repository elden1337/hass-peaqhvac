from datetime import datetime

class Offset:
    tolerance = 3

    def getoffset(
            self,
            prices: list,
            prices_tomorrow: list,
            hour: int = datetime.now().hour
    ) -> int:
        current_hour = prices[hour]
        adjustment = ((current_hour / self._getaverage(prices, prices_tomorrow)) - 1) * -1 * self.tolerance
        return int(min(adjustment, self.tolerance) if adjustment > 0 else max(adjustment, self.tolerance * -1))

    def _getaverage(self, prices: list, prices_tomorrow: list = None) -> float:
        total = prices
        if prices_tomorrow is not None and len(prices_tomorrow) == 24:
            for price in prices_tomorrow:
                total.append(price)
        return sum(total) / len(total)

    #def calc with trend temp
    #def calc with prognosis
    #def calc with current outside vs set temp


# PRICES = [2.671, 3.505, 2.927, 2.927, 3.341, 3.875, 6.308, 6.947, 7.012, 6.697, 6.28, 6.018, 5.251, 5.217, 5.3, 5.345,
#           5.808, 6.794, 7.06, 7.349, 6.705, 4.484, 3.341, 1.95]
# PRICES_TOMORROW = [1.241, 1.684, 1.604, 1.647, 2.547, 1.268, 4.438, 6.538, 6.786, 6.367, 5.625, 4.01, 3.839, 3.567,
#                    1.982, 3.319, 3.867, 5.871, 6.285, 6.414, 6.16, 4.476, 1.161, 0.987]
# HOUR = 13
#
# test = Offset().getoffset(PRICES, PRICES_TOMORROW, HOUR)
# print(test)