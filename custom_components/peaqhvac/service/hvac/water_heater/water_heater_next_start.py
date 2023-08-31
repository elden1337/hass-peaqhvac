from statistics import mean
from datetime import datetime, timedelta
import logging

_LOGGER = logging.getLogger(__name__)

HOUR_LIMIT = 18
DELAY_LIMIT = 48


class NextWaterBoost:
    def __init__(self):
        self.prices = []
        self.now_dt: datetime|None = None
        self.floating_mean: float|None = None

    def next_predicted_demand(
            self,
            prices: list,
            min_demand: int,
            temp: float,
            temp_trend: float,
            target_temp: float,
            now_dt=None
    ) -> datetime:
        self._init_vars(prices, now_dt)
        try:
            delay = (target_temp - temp) / temp_trend
        except ZeroDivisionError:
            delay = DELAY_LIMIT
        return self.get_next_start(
            self.prices,
            min_demand,
            self.now_dt,
            self.now_dt + timedelta(hours=delay),
            cold=False
        )

    def get_next_start(self, prices: list, demand: int, now_dt=None, delay_dt=None, cold=True) -> datetime:
        self._init_vars(prices, now_dt)
        try:
            last_known_price = self.now_dt.replace(hour=0, minute=0, second=0) + timedelta(hours=len(self.prices) - 1)
        except Exception as e:
            _LOGGER.error(
                f"Error on getting last known price with {self.now_dt} and len prices {len(self.prices)}: {e}")
            return datetime.max
        if last_known_price - self.now_dt > timedelta(hours=18) and not cold:
            print("case A")
            return self._calculate_last_start(demand)
        _next_dt = self._calculate_next_start(demand)
        if not delay_dt:
            print("case B")
            return _next_dt
        if _next_dt < delay_dt:
            print("case C")
            return self._calculate_last_start(demand)
        print("case D")
        return _next_dt

    def _init_vars(self, prices: list, now_dt=None) -> None:
        self.prices = prices
        self._set_now_dt(now_dt)
        self._set_floating_mean()

    def _set_now_dt(self, now_dt=None) -> None:
        self.now_dt = datetime.now() if now_dt is None else now_dt

    def _set_floating_mean(self, now_dt=None) -> float:
        self.floating_mean = mean(self.prices[self.now_dt.hour:])

    def _set_start_dt(self, demand: int, low_period: int, delayed_dt: datetime = None, delayed: bool = False) -> datetime:
        now_dt = self.now_dt if delayed_dt is None else delayed_dt
        start_minute: int = now_dt.minute
        if low_period >= 60 - now_dt.minute:
            """delayed start"""
            if not delayed:
                start_minute = max(now_dt.minute, min(60 - int(demand / 2), 59))
            else:
                start_minute = min(60 - int(demand / 2), 59)
        return now_dt.replace(minute=start_minute, second=0, microsecond=0)

    def _get_low_period(self, override_dt=None) -> int:
        dt = self.now_dt if override_dt is None else override_dt
        if override_dt is not None:
            _start_hour = dt.hour + (int(self.now_dt.day != override_dt.day) * 24)
        else:
            _start_hour = dt.hour
        low_period: int = 0
        for i in range(_start_hour, len(self.prices)):
            if self.prices[i] > self.floating_mean:
                break
            if i == dt.hour:
                low_period = 60 - dt.minute
            else:
                low_period += 60
        return low_period

    def _values_are_good(self, i) -> bool:
        return all([
            self.prices[i] < self.floating_mean,
            self.prices[i + 1] < self.floating_mean])

    def _calculate_next_start(self, demand: int) -> datetime:
        try:
            if self.prices[self.now_dt.hour] < self.floating_mean:
                """This hour is cheap enough to start"""
                low_period = self._get_low_period()
                return self._set_start_dt(demand=demand, low_period=low_period)
            for i in range(self.now_dt.hour, len(self.prices) - 1):
                """Search forward for other hours to start"""
                if self._values_are_good(i):
                    return self._set_start_dt_params(i, demand)
        except Exception as e:
            _LOGGER.error(f"Error on getting next start: {e}")
            return datetime.max

    def _calculate_last_start(self, demand: int) -> datetime:
        try:
            _param_i = None
            for i in range(self.now_dt.hour,
                           min(len(self.prices) - 1, self.now_dt.hour + HOUR_LIMIT)):
                if self._values_are_good(i):
                    _param_i = i
                else:
                    break
            if _param_i is None:
                return self._calculate_last_start_reverse(demand)
            return self._set_start_dt_params(_param_i, demand)
        except Exception as e:
            _LOGGER.error(f"Error on getting last close start: {e}")
            return datetime.max

    def _calculate_last_start_reverse(self, demand: int):
        try:
            for i in reversed(range(self.now_dt.hour,
                                    min(len(self.prices) - 1, self.now_dt.hour + HOUR_LIMIT))):
                if self._values_are_good(i):
                    return self._set_start_dt_params(i, demand)
        except Exception as e:
            _LOGGER.error(f"Error on getting last start: {e}")
            return datetime.max

    def _set_start_dt_params(self, i: int, demand: int) -> datetime:
        delay = (i - self.now_dt.hour)
        delayed_dt = self.now_dt + timedelta(hours=delay)
        low_period = self._get_low_period(override_dt=delayed_dt)
        _LOGGER.debug(f"delay: {delay}, low_period: {low_period}, delayed_dt: {delayed_dt}. now_dt = {self.now_dt}")
        return self._set_start_dt(demand, low_period, delayed_dt, True)