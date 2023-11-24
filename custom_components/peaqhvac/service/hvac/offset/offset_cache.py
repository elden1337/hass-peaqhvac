from datetime import datetime, date, timedelta
from dataclasses import dataclass
from typing import List
import logging

_LOGGER = logging.getLogger(__name__)

@dataclass
class CacheDict:
    today: bool
    prices: List[float]
    offsets: List[float]
    dt: date


_offsetCache: List[CacheDict] = []

def get_cache(dt: date) -> CacheDict:
    for h in _offsetCache:
        if h.dt == dt:
            return h
    return None

def update_cache(list_dt: date, prices: List[float], offsets: List[float], now_dt: datetime = datetime.now()):
    if len(prices) < 1 or len(offsets) < 1:
        """Don't update cache if no data is available"""
        return

    data = [h.dt for h in _offsetCache]

    if now_dt.date() == list_dt:
        """This item is regarding today"""
        if list_dt in data:
            for h in _offsetCache:
                if h.dt == list_dt and not h.today:
                    _LOGGER.debug("Updating existing today-item")
                    h.today = True
        elif now_dt.date() not in data:
            _offsetCache.append(CacheDict(True, prices, offsets, now_dt.date()))
    else:
        """This item is regarding tomorrow"""
        if list_dt not in data:
            _offsetCache.append(CacheDict(False, prices, offsets, list_dt))
        else:
            for h in _offsetCache:
                if h.dt != now_dt:
                    h.today = False

    # """Remove old items"""
    for h in _offsetCache:
        if h.dt < date.today() - timedelta(days=2):
            _offsetCache.remove(h)



# Usage
# update_cache(now_dt=datetime(2023, 1, 1, 0, 0, 3), list_dt=date(2023, 1, 1), prices=[1], offsets=[1, 2, 3])
# update_cache(now_dt=datetime(2023, 1, 1, 13, 0, 3), list_dt=date(2023, 1, 2), prices=[2], offsets=[1, 2, 3])
# update_cache(now_dt=datetime(2023, 1, 2, 0, 0, 3), list_dt=date(2023, 1, 2), prices=[3], offsets=[1, 2, 3])
#
# for i in _offsetCache:
#     print(i)