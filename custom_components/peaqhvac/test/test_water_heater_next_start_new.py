import pytest
from datetime import datetime
from ..service.hvac.water_heater.water_heater_next_start import (
    NextWaterBoost,
    NextStartPostModel,
)


P240126 = [
    0.97,
    0.94,
    0.91,
    0.87,
    0.86,
    0.82,
    0.9,
    0.97,
    1,
    0.98,
    0.95,
    0.91,
    0.82,
    0.74,
    0.78,
    0.77,
    0.81,
    0.89,
    0.85,
    0.55,
    0.47,
    0.44,
    0.42,
    0.39,
]
P240129 = [
    0.07,
    0.05,
    0.05,
    0.05,
    0.06,
    0.08,
    0.16,
    0.35,
    0.37,
    0.43,
    0.65,
    0.76,
    0.97,
    0.97,
    0.98,
    1.34,
    1.57,
    1.83,
    1.69,
    1.55,
    1.34,
    1.24,
    0.99,
    0.96,
]
P240130 = [
    0.93,
    0.79,
    0.76,
    0.76,
    0.76,
    0.93,
    0.96,
    1.08,
    1.26,
    1.24,
    1.14,
    1,
    0.98,
    0.98,
    0.99,
    0.97,
    0.98,
    1.07,
    0.95,
    0.91,
    0.88,
    0.84,
    0.4,
    0.42,
]
P240131 = [
    0.34,
    0.34,
    0.34,
    0.34,
    0.35,
    0.35,
    0.44,
    0.87,
    0.9,
    0.53,
    0.37,
    0.35,
    0.34,
    0.33,
    0.32,
    0.31,
    0.32,
    0.31,
    0.22,
    0.13,
    0.08,
    0.08,
    0.07,
    0.05,
]
P240201 = [
    0.05,
    0.05,
    0.04,
    0.04,
    0.05,
    0.05,
    0.08,
    0.12,
    0.13,
    0.14,
    0.13,
    0.12,
    0.13,
    0.12,
    0.13,
    0.15,
    0.25,
    0.57,
    0.65,
    0.28,
    0.31,
    0.3,
    0.25,
    0.18,
]
P240202 = [
    0.19,
    0.21,
    0.21,
    0.23,
    0.24,
    0.26,
    0.37,
    0.9,
    0.93,
    0.9,
    0.88,
    0.69,
    0.43,
    0.41,
    0.4,
    0.4,
    0.38,
    0.37,
    0.34,
    0.28,
    0.24,
    0.18,
    0.09,
    0.08,
]
P240203 = [
    0.06,
    0.06,
    0.05,
    0.05,
    0.05,
    0.05,
    0.07,
    0.08,
    0.08,
    0.11,
    0.11,
    0.08,
    0.08,
    0.08,
    0.08,
    0.09,
    0.13,
    0.22,
    0.22,
    0.13,
    0.08,
    0.1,
    0.08,
    0.08,
]
P240314 = [
    0.45,
    0.37,
    0.34,
    0.26,
    0.28,
    0.36,
    0.45,
    0.5,
    0.5,
    0.5,
    0.5,
    0.51,
    0.5,
    0.48,
    0.46,
    0.43,
    0.39,
    0.37,
    0.4,
    0.35,
    0.28,
    0.13,
    0.08,
    0.08,
]
P240315 = [
    0.08,
    0.08,
    0.08,
    0.08,
    0.08,
    0.27,
    0.46,
    0.57,
    0.63,
    0.67,
    0.71,
    0.63,
    0.62,
    0.61,
    0.69,
    0.78,
    0.8,
    0.86,
    0.87,
    0.81,
    0.76,
    0.69,
    0.64,
    0.61,
]


def test1():
    tt = NextWaterBoost()
    model = NextStartPostModel(
        prices=P240126,
        demand_hours=[20, 21],
        non_hours=[12, 17, 11, 16],
        current_temp=41.2,
        temp_trend=0,
        latest_boost=datetime(2024, 1, 25, 6, 52),
        dt=datetime(2024, 1, 26, 13, 2, 0),
    )
    ret = tt.get_next_start(model)
    assert ret.next_start == datetime(2024, 1, 26, 20, 50, 0)
    assert ret.target_temp == 47


def test2():
    tt = NextWaterBoost()
    model = NextStartPostModel(
        prices=P240129,
        demand_hours=[],
        non_hours=[12, 17, 11, 16],
        current_temp=37,
        temp_trend=0,
        latest_boost=datetime(2024, 1, 29, 0, 2),
        dt=datetime(2024, 1, 29, 12, 30, 0),
    )
    ret = tt.get_next_start(model)
    assert ret.next_start == datetime(2024, 1, 29, 23, 50, 0)
    assert ret.target_temp == 46


def test3():
    tt = NextWaterBoost()
    model = NextStartPostModel(
        prices=P240130 + P240131,
        demand_hours=[20, 21],
        non_hours=[12, 17, 11, 16],
        current_temp=12,
        temp_trend=-40,
        latest_boost=datetime(2024, 1, 30, 20, 40),
        dt=datetime(2024, 1, 30, 20, 55, 0),
    )
    ret = tt.get_next_start(model)
    assert ret.next_start == datetime(2024, 1, 30, 22, 50, 0)
    assert ret.target_temp == 25


def test4():
    tt = NextWaterBoost()
    model = NextStartPostModel(
        prices=P240201 + P240202,
        demand_hours=[20, 21],
        non_hours=[12, 17, 11, 16],
        current_temp=52.6,
        temp_trend=-1.78,
        latest_boost=datetime(2024, 2, 1, 14, 42),
        dt=datetime(2024, 2, 1, 17, 30, 0),
    )
    ret = tt.get_next_start(model)
    assert ret.next_start == datetime(2024, 2, 1, 23, 50, 0)
    assert ret.target_temp == 47


def test5():
    tt = NextWaterBoost()
    model = NextStartPostModel(
        prices=P240202 + P240203,
        demand_hours=[20, 21],
        non_hours=[12, 17, 11, 16],
        current_temp=44.1,
        temp_trend=0,
        latest_boost=datetime(2024, 2, 2, 14, 42),
        dt=datetime(2024, 2, 2, 20, 25, 0),
    )
    ret = tt.get_next_start(model)
    assert ret.next_start == datetime(2024, 2, 3, 2, 50, 0)
    assert ret.target_temp == 47


def test6():
    tt = NextWaterBoost()
    model = NextStartPostModel(
        prices=P240202 + P240203,
        demand_hours=[20, 21],
        non_hours=[12, 17, 11, 16],
        current_temp=38.1,
        temp_trend=0,
        latest_boost=datetime(2024, 2, 2, 14, 42),
        dt=datetime(2024, 2, 3, 2, 50, 1),
    )
    ret = tt.get_next_start(model)
    assert ret.next_start == datetime(2024, 2, 3, 2, 50, 0)
    assert ret.target_temp == 47


def test_below_min_hours_should_heat_more():
    tt = NextWaterBoost()
    model = NextStartPostModel(
        prices=P240314 + P240315,
        demand_hours=[],
        non_hours=[],
        current_temp=48.5,
        temp_trend=0,
        min_price=0.1,
        latest_boost=datetime(2024, 3, 13, 23, 50),
        dt=datetime(2024, 3, 14, 20, 9, 1),
    )
    ret = tt.get_next_start(model)
    assert ret.next_start == datetime(2024, 3, 15, 3, 50, 0)
    assert ret.target_temp == 53
