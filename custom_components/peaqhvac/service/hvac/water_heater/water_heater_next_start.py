from statistics import mean
from datetime import datetime, timedelta
import logging

_LOGGER = logging.getLogger(__name__)

def _set_start_dt(demand: int, low_period: int, now_dt=None, delayed: bool = False) -> datetime:
    now_dt = datetime.now() if now_dt is None else now_dt
    start_minute: int = now_dt.minute
    if low_period >= 60 - now_dt.minute:
        """delayed start"""
        if not delayed:
            start_minute = max(now_dt.minute, min(60 - int(demand / 2), 59))
        else:
            start_minute = min(60 - int(demand / 2), 59)
    return now_dt.replace(minute=start_minute, second=0, microsecond=0)


def _get_low_period(prices:list, now_dt=None) -> int:
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


def get_next_start(prices:list, demand:int, now_dt=None, delay_dt=None) -> datetime:
    now_dt = datetime.now() if now_dt is None else now_dt
    last_known_price = now_dt.replace(hour=0,minute=0,second=0) + timedelta(hours=len(prices)-1)
    if delay_dt is None or delay_dt < last_known_price:
        """There should be a low period ahead."""
        return _calculate_next_start(now_dt, demand, prices)
    elif last_known_price - now_dt > timedelta(hours=18):
        """There are too many expensive hours ahead. We should pre-heat to avoid expensive hours."""
        return _calculate_last_start(now_dt, demand, prices)
    return datetime.max


def _calculate_next_start(now_dt:datetime, demand:int, prices:list):
    try:
        if prices[now_dt.hour] < mean(prices):
            low_period = _get_low_period(prices, now_dt)
            return _set_start_dt(demand, low_period, now_dt)
        for i in range(now_dt.hour, len(prices)-1):
            if prices[i] < mean(prices) and prices[i+1] < mean(prices):
                return _set_start_dt_params(now_dt, i, prices, demand)
    except Exception as e:
        _LOGGER.error(f"Error on getting next start: {e}")
        return datetime.max


def _calculate_last_start(now_dt:datetime, demand:int, prices:list):
    try:
        for i in reversed(range(now_dt.hour, min(len(prices)-1, now_dt.hour + 18))):
            if prices[i] < mean(prices) and prices[i+1] < mean(prices):
                return _set_start_dt_params(now_dt, i, prices, demand)
    except Exception as e:
        _LOGGER.error(f"Error on getting last start: {e}")
        return datetime.max


def _set_start_dt_params(now_dt: datetime, i:int, prices:list, demand:int) -> datetime:
    delay = (i - now_dt.hour)
    delayed_dt = now_dt + timedelta(hours=delay)
    low_period =_get_low_period(prices, delayed_dt)
    return _set_start_dt(demand, low_period, delayed_dt, True)


def next_predicted_demand(prices:list, min_demand:int, temp:float, temp_trend:float, target_temp:float, now_dt=None) -> datetime:
    now_dt = datetime.now() if now_dt is None else now_dt
    if temp_trend < 0:
        delay = (target_temp - temp) / temp_trend
        #print(f"delay: {now_dt + timedelta(hours=delay)}")
        #print(f"mean: {mean(prices)}")
        return get_next_start(prices, min_demand,now_dt, now_dt + timedelta(hours=delay))
    return datetime.max


# prices =[0.29,0.27,0.25,0.23,0.23,0.2,0.18,0.23,0.27,0.29,0.29,0.3,0.26,0.29,0.3,0.3,0.34,1.62,1.82,1.96,1.9,1.93,0.43,0.4]
# prices_tomorrow =[0.44,0.43,0.45,0.46,0.52,1.44,1.74,2.17,2.25,1.94,1.82,1.79,1.65,1.57,1.54,1.79,1.82,2.32,2.51,2.69,2.57,2.15,0.67,0.49]
# prices_combined = prices + prices_tomorrow
# mockdt = datetime(2023,8,26,18,43,0)
# demand = 80 #derived from demand_enum
# min_demand = 20

# print(f"next start vanilla: {get_next_start(prices_combined, demand, mockdt)}")
# print(f"next start with delay: {next_predicted_demand(prices_combined, min_demand, 50, -0.3, 40, mockdt)}")