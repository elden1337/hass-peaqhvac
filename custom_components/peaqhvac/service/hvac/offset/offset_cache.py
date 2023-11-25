from datetime import datetime, date, timedelta
from dataclasses import dataclass, field
from typing import List
import logging
import uuid

_LOGGER = logging.getLogger(__name__)


@dataclass
class CacheDict:
    id: uuid = field(init=False)
    today: bool
    prices: List[float]
    offsets: List[float]
    dt: date

    def __post_init__(self):
        self.id = uuid.uuid4()


_offsetCache: List[CacheDict] = []


def get_cache(dt: date) -> CacheDict:
    for h in _offsetCache:
        if h.dt == dt:
            return h
    return None


def get_cache_for_today(dt: date, prices: list) -> CacheDict:
    for h in _offsetCache:
        if h.dt == dt and h.prices == prices:
            h.today = True
            for h2 in _offsetCache:
                if h2.id != h.id:
                    h2.today = False
            return h
    return None


def update_cache(list_dt: date, prices: List[float], offsets: List[float], now_dt: datetime = datetime.now()):
    global _offsetCache
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
    """Remove old items"""
    _offsetCache = [h for h in _offsetCache if h.dt >= now_dt.date() - timedelta(days=2)]

# Usage
# update_cache(now_dt=datetime(2023, 1, 1, 0, 0, 3), list_dt=date(2023, 1, 1), prices=[1], offsets=[1, 2, 3])
# update_cache(now_dt=datetime(2023, 1, 1, 13, 0, 3), list_dt=date(2023, 1, 2), prices=[2], offsets=[1, 2, 3])
# update_cache(now_dt=datetime(2023, 1, 2, 0, 0, 3), list_dt=date(2023, 1, 2), prices=[3], offsets=[1, 2, 3])
#
# for i in _offsetCache:
#     print(i)