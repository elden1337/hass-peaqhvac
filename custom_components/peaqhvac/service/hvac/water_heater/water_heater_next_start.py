from statistics import mean
from datetime import datetime, timedelta
import logging

_LOGGER = logging.getLogger(__name__)

def _set_start_dt(demand: int, low_period: int, now_dt=None, delayed: bool = False) -> datetime:
    now_dt = datetime.now() if now_dt is None else now_dt
    start_minute: int = now_dt.minute
    if _is_low_multiple_hours(low_period, now_dt):
        """delayed start"""
        if not delayed:
            start_minute = max(now_dt.minute, min(60 - int(demand / 2), 59))
        else:
            start_minute = min(60 - int(demand / 2), 59)
    return now_dt.replace(minute=start_minute, second=0, microsecond=0)


def _is_low_multiple_hours(low_period, now_dt) -> bool:
    return low_period >= 60 - now_dt.minute


def _get_low_period(prices, now_dt=None) -> int:
    now_dt = datetime.now() if now_dt is None else now_dt
    low_period: int = 0
    for i in range(now_dt.hour, len(prices)):
        if prices[i] > mean(prices):
            break
        if i == now_dt.hour:
            low_period = 60 - now_dt.minute
        else:
            low_period += 60
    return low_period


def get_next_start(prices, demand, now_dt=None) -> datetime:
    now_dt = datetime.now() if now_dt is None else now_dt
    try:
        if prices[now_dt.hour] < mean(prices):
            return _set_start_dt(demand, _get_low_period(prices, now_dt), now_dt)
        for i in range(now_dt.hour + 1, len(prices)):
            if prices[i] < mean(prices):
                delay = (i - now_dt.hour) * 60
                delayed_dt = now_dt + timedelta(minutes=delay)
                return _set_start_dt(demand, _get_low_period(prices, delayed_dt), delayed_dt, True)
    except Exception as e:
        _LOGGER.error(f"Error on getting next start: {e}")
    return datetime.max


def next_predicted_demand(prices:list, min_demand:int, temp:float, temp_trend:float, target_temp:float, now_dt=None) -> datetime:
    now_dt = datetime.now() if now_dt is None else now_dt
    if temp_trend < 0:
        delay = (target_temp - temp) / temp_trend
        return get_next_start(prices, min_demand, now_dt + timedelta(hours=delay))
    return datetime.max