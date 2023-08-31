from statistics import mean
from datetime import datetime, timedelta
import logging

_LOGGER = logging.getLogger(__name__)

HOUR_LIMIT = 18
DELAY_LIMIT = 48


class NextWaterBoost:
    prices: list = []
    now_dt: datetime = datetime.max
    floating_mean: float = 0

    @staticmethod
    def next_predicted_demand(prices: list, min_demand: int, temp: float, temp_trend: float, target_temp: float,
                              now_dt=None) -> datetime:
        NextWaterBoost._init_vars(prices, now_dt)
        try:
            delay = (target_temp - temp) / temp_trend
        except ZeroDivisionError:
            delay = DELAY_LIMIT
        return NextWaterBoost.get_next_start(prices, min_demand, NextWaterBoost.now_dt,
                                             NextWaterBoost.now_dt + timedelta(hours=delay), cold=False)

    @staticmethod
    def get_next_start(prices: list, demand: int, now_dt=None, delay_dt=None, cold=True) -> datetime:
        NextWaterBoost._init_vars(prices, now_dt)
        last_known_price = now_dt.replace(hour=0, minute=0, second=0) + timedelta(hours=len(prices) - 1)
        if last_known_price - now_dt > timedelta(hours=18) and not cold:
            print("case A")
            return NextWaterBoost._calculate_last_start(demand)
        _next_dt = NextWaterBoost._calculate_next_start(demand)
        if not delay_dt:
            print("case B")
            return _next_dt
        if _next_dt < delay_dt:
            print("case C")
            return NextWaterBoost._calculate_last_start(demand)
        print("case D")
        return _next_dt

    @staticmethod
    def _init_vars(prices: list, now_dt: datetime) -> None:
        NextWaterBoost.prices = prices
        NextWaterBoost._set_now_dt(now_dt)
        NextWaterBoost._set_floating_mean()

    @staticmethod
    def _set_now_dt(now_dt=None) -> None:
        NextWaterBoost.now_dt = datetime.now() if now_dt is None else now_dt
        NextWaterBoost._set_floating_mean()

    @staticmethod
    def _set_floating_mean(now_dt=None) -> float:
        NextWaterBoost.floating_mean = mean(NextWaterBoost.prices[NextWaterBoost.now_dt.hour:])

    @staticmethod
    def _set_start_dt(demand: int, low_period: int, delayed_dt: datetime = None, delayed: bool = False) -> datetime:
        now_dt = NextWaterBoost.now_dt if delayed_dt is None else delayed_dt
        start_minute: int = now_dt.minute
        if low_period >= 60 - now_dt.minute:
            """delayed start"""
            if not delayed:
                start_minute = max(now_dt.minute, min(60 - int(demand / 2), 59))
            else:
                start_minute = min(60 - int(demand / 2), 59)
        return now_dt.replace(minute=start_minute, second=0, microsecond=0)

    @staticmethod
    def _get_low_period(override_dt=None) -> int:
        dt = NextWaterBoost.now_dt if override_dt is None else override_dt
        low_period: int = 0
        for i in range(dt.hour, len(NextWaterBoost.prices)):
            if NextWaterBoost.prices[i] > NextWaterBoost.floating_mean:
                break
            if i == dt.hour:
                low_period = 60 - dt.minute
            else:
                low_period += 60
        return low_period

    @staticmethod
    def _values_are_good(i) -> bool:
        return all([
            NextWaterBoost.prices[i] < NextWaterBoost.floating_mean,
            NextWaterBoost.prices[i + 1] < NextWaterBoost.floating_mean])

    @staticmethod
    def _calculate_next_start(demand: int) -> datetime:
        try:
            if NextWaterBoost.prices[NextWaterBoost.now_dt.hour] < NextWaterBoost.floating_mean:
                low_period = NextWaterBoost._get_low_period()
                return NextWaterBoost._set_start_dt(demand, low_period)
            for i in range(NextWaterBoost.now_dt.hour, len(NextWaterBoost.prices) - 1):
                if NextWaterBoost._values_are_good(i):
                    return NextWaterBoost._set_start_dt_params(i, demand)
        except Exception as e:
            _LOGGER.error(f"Error on getting next start: {e}")
            return datetime.max

    @staticmethod
    def _calculate_last_start(demand: int) -> datetime:
        try:
            _param_i = None
            for i in range(NextWaterBoost.now_dt.hour,
                           min(len(NextWaterBoost.prices) - 1, NextWaterBoost.now_dt.hour + HOUR_LIMIT)):
                if NextWaterBoost._values_are_good(i):
                    _param_i = i
                else:
                    break
            if _param_i is None:
                return NextWaterBoost._calculate_last_start_reverse(demand)
            return NextWaterBoost._set_start_dt_params(_param_i, demand)
        except Exception as e:
            _LOGGER.error(f"Error on getting last close start: {e}")
            return datetime.max

    @staticmethod
    def _calculate_last_start_reverse(demand: int):
        try:
            for i in reversed(range(NextWaterBoost.now_dt.hour,
                                    min(len(NextWaterBoost.prices) - 1, NextWaterBoost.now_dt.hour + HOUR_LIMIT))):
                if NextWaterBoost._values_are_good(i):
                    return NextWaterBoost._set_start_dt_params(i, demand)
        except Exception as e:
            _LOGGER.error(f"Error on getting last start: {e}")
            return datetime.max

    @staticmethod
    def _set_start_dt_params(i: int, demand: int) -> datetime:
        delay = (i - NextWaterBoost.now_dt.hour)
        delayed_dt = NextWaterBoost.now_dt + timedelta(hours=delay)
        low_period = NextWaterBoost._get_low_period(delayed_dt)
        return NextWaterBoost._set_start_dt(demand, low_period, delayed_dt, True)