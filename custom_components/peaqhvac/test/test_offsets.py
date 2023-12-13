import pytest
from datetime import datetime, timedelta
from ..service.hvac.offset.offset_utils import (
    max_price_lower_internal, offset_per_day, set_offset_dict)
# from custom_components.peaqhvac.service.hvac.offset.offset_utils import (
#     max_price_lower_internal, offset_per_day, set_offset_dict)

def test_offsets_cent_and_normal_match():
    prices = [1.17,1.14,1.14,1.11,1.11,1.14,1.25,1.59,2.09,2.09,2.13,2.14,2.14,1.61,1.59,1.62,1.61,1.68,1.61,1.52,1.44,1.36,1.38,1.27,1.17,1.15,1.16,1.16,1.19,1.24,1.47,1.81,1.97,2.19,2.19,1.92,1.81,1.99,2.19,2.73,2.73,2.63,2.11,1.81,1.62,1.43,1.41,1.28]
    now_dt = datetime(2023,12,13,20,43,0)
    r1 = set_offset_dict(prices, now_dt, 0, {})
    r2 = set_offset_dict([p*100 for p in prices], now_dt, 0, {})

    assert r1 == r2

