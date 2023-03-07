import time
import logging
from datetime import datetime
from stat import mean

_LOGGER = logging.getLogger(__name__)

def get_water_peak(hour: int, prices:list, avg_monthly_price: float = None) -> bool:    
    try:
        ret = all([
            any([
                __condition1(hour, prices, avg_monthly_price),
                __condition2(hour, prices)
            ]),
            prices[hour] < mean(prices) / 2
        ])
        return ret
    except Exception as e:
        _LOGGER.debug(f"Could not calc peak water hours for hour {hour}. pricelist is {len(prices)} long, {e}")
    return False
        
def __condition1(hour, prices, avg_monthly_price) -> bool:
    try:
        cond1  = all([
        prices[hour] == min(prices),
        datetime.now().minute > 20
    ])
        if avg_monthly_price is not None:
            return all([
                cond1,
                avg_monthly_price > prices[hour]
            ])
        else:
            return cond1
    except Exception as e:
        _LOGGER.debug(f"Condition1 failed: {e}")

def __condition2(hour, prices) -> bool:
    try:
        return all([
            prices[hour + 1] == min(prices),
            prices[hour + 1] / prices[hour] >= 0.7,
            datetime.now().minute >= 30
        ])
    except Exception as e:
        _LOGGER.debug(f"Condition2 failed: {e}")