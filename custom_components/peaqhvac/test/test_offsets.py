import pytest
from datetime import datetime, timedelta
import random
from ..service.hvac.house_heater.models.calculated_offset import CalculatedOffsetModel
from ..service.hvac.offset.offset_utils import (offset_per_day, set_offset_dict, adjust_to_threshold)
from ..service.hvac.offset.peakfinder import smooth_transitions
from ..service.models.enums.hvac_presets import HvacPresets

P231213 = [1.17, 1.14, 1.14, 1.11, 1.11, 1.14, 1.25, 1.59, 2.09, 2.09, 2.13, 2.14,
              2.14, 1.61, 1.59, 1.62, 1.61, 1.68, 1.61, 1.52, 1.44, 1.36, 1.38, 1.27]
P231214 = [1.17, 1.15, 1.16, 1.16, 1.19, 1.24, 1.47, 1.81, 1.97, 2.19, 2.19, 1.92,
              1.81, 1.99, 2.19, 2.73, 2.73, 2.63, 2.11, 1.81, 1.62, 1.43, 1.41, 1.28]
P231215 =[1.28,1.24,1.2,1.15,1.13,1.2,1.42,1.57,1.78,1.72,1.61,1.51,1.39,1.31,1.28,1.3,1.42,1.37,1.26,1.19,1.15,1.14,0.93,1.05]
P231216 = [0.69,0.62,0.56,0.45,0.38,0.32,0.31,0.31,0.31,0.3,0.3,0.27,0.26,0.25,0.26,0.27,0.28,0.27,0.24,0.23,0.15,0.11,0.08,0.08]

def test_offsets_cent_and_normal_match():
    prices = P231213 + P231214
    now_dt = datetime(2023,12,13,20,43,0)
    r1 = set_offset_dict(prices, now_dt, 0, {})
    r2 = set_offset_dict([p*100 for p in prices], now_dt, 0, {})
    assert r1 == r2

def test_offsets_correct_curve_over_night_cached_today():
    _tolerance = 3
    indoors_preset = HvacPresets.Normal
    prices = P231215
    prices_tomorrow =  P231216
    now_dt = datetime(2023,12,15,0,3,0)
    offset_dict1 = set_offset_dict(prices, now_dt, 0, {})
    today1 = offset_per_day(
        all_prices=prices,
        day_values=offset_dict1[now_dt.date()],
        tolerance=_tolerance,
        indoors_preset=indoors_preset,
    )

    ret1 = smooth_transitions(
        today=today1,
        tomorrow=[],
        tolerance=_tolerance,
    )
    key_today_only = [1,1,2,2,3,2,-2,-3,-3,-3,-3,-3,-1,0,1,0,-2,-1,1,2,2,3,-3,-3]
    assert [v for k,v in ret1[0].items()] == key_today_only

    now_dt = datetime(2023,12,15,13,3,0)
    existing_mock = {now_dt.date(): ret1[0]}
    offset_dict2 = set_offset_dict(prices+prices_tomorrow, now_dt, 0, existing_mock)
    today2 = offset_per_day(
        all_prices=prices + prices_tomorrow,
        day_values=offset_dict2[now_dt.date()],
        tolerance=_tolerance,
        indoors_preset=indoors_preset,
    )
    tomorrow2 = offset_per_day(
        all_prices=prices + prices_tomorrow,
        day_values=offset_dict2[(now_dt + timedelta(days=1)).date()],
        tolerance=_tolerance,
        indoors_preset=indoors_preset,
    )

    ret2 = smooth_transitions(
        today=today2,
        tomorrow=tomorrow2,
        tolerance=_tolerance,
    )

    key_today = [-3,-3,-3,-3,-3,-3, -3, -3, -3, -3, -3, -2, 3, 0, -2, -2, -3, -3, -2, -2, -2, -2, -1, -2]
    key_tomorrow = [0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 2, 2, 2]
    assert [v for k, v in ret2[0].items()] == key_today
    assert [v for k, v in ret2[1].items()] == key_tomorrow


def test_smooth_transistions_no_weather_prog_nothing_exceeds_tolerance():
    _tolerance = 3
    indoors_preset = HvacPresets.Normal
    prices = P231213
    prices_tomorrow = P231214
    now_dt = datetime(2023, 12, 13, 20, 43, 0)
    offset_dict = set_offset_dict(prices+prices_tomorrow, now_dt, 0, {})

    today = offset_per_day(
        all_prices=prices + prices_tomorrow,
        day_values=offset_dict[now_dt.date()],
        tolerance=_tolerance,
        indoors_preset=indoors_preset,
    )
    tomorrow = offset_per_day(
        all_prices=prices + prices_tomorrow,
        day_values=offset_dict[(now_dt + timedelta(days=1)).date()],
        tolerance=_tolerance,
        indoors_preset=indoors_preset,
    )

    ret = smooth_transitions(
            today=today,
            tomorrow=tomorrow,
            tolerance=_tolerance,
        )

    assert all([abs(v) <= _tolerance for k,v in ret[0].items()])
    assert all([abs(v) <= _tolerance for k, v in ret[1].items()])

def test_adjust_to_treshold_no_exceeding_values():
    _tolerance = 3
    indoors_preset = HvacPresets.Normal
    prices = P231213
    prices_tomorrow = P231214
    now_dt = datetime(2023, 12, 13, 20, 43, 0)
    offset_dict = set_offset_dict(prices + prices_tomorrow, now_dt, 0, {})

    today = offset_per_day(
        all_prices=prices + prices_tomorrow,
        day_values=offset_dict[now_dt.date()],
        tolerance=_tolerance,
        indoors_preset=indoors_preset,
    )
    tomorrow = offset_per_day(
        all_prices=prices + prices_tomorrow,
        day_values=offset_dict[(now_dt + timedelta(days=1)).date()],
        tolerance=_tolerance,
        indoors_preset=indoors_preset,
    )

    smooth = smooth_transitions(
        today=today,
        tomorrow=tomorrow,
        tolerance=_tolerance,
    )

    for k,v in smooth[0].items():
        model = CalculatedOffsetModel(current_offset=v, current_tempdiff=random.uniform(-1, 1), current_temp_extremas=random.uniform(-1, 1), current_temp_trend_offset=random.uniform(-1, 1))
        adj = adjust_to_threshold(model, 0, _tolerance)
        assert abs(adj) <= _tolerance
    for k,v in smooth[1].items():
        model = CalculatedOffsetModel(current_offset=v, current_tempdiff=random.uniform(-1, 1), current_temp_extremas=random.uniform(-1, 1), current_temp_trend_offset=random.uniform(-1, 1))
        adj = adjust_to_threshold(model, 0, _tolerance)
        assert abs(adj) <= _tolerance

