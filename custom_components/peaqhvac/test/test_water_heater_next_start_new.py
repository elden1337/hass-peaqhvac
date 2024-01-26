import pytest
from datetime import datetime, timedelta
from ..service.hvac.water_heater.water_heater_next_start import get_next_start


P240126 = [0.97,0.94,0.91,0.87,0.86,0.82,0.9,0.97,1,0.98,0.95,0.91,0.82,0.74,0.78,0.77,0.81,0.89,0.85,0.55,0.47,0.44,0.42,0.39]

def test1():
    tt = get_next_start(
        prices=P240126,
        demand_hours=[20,21],
        non_hours=[12,17,11,16],
        current_temp=41.2,
        temp_trend=0,
        latest_boost=datetime(2024,1,25, 6,52),
        mock_dt=datetime(2024,1,26,13,2,0)
    )
    assert tt[0] == datetime(2024,1,26,19,50,0)

def test2():
    tt = get_next_start(
        prices=P240126,
        demand_hours=[20,21],
        non_hours=[12,17,11,16],
        current_temp=41.2,
        temp_trend=0,
        latest_boost=datetime(2024,1,26, 12,52),
        mock_dt=datetime(2024,1,26,13,2,0)
    )
    assert tt[0] == datetime.max

def test3():
    tt = get_next_start(
        prices=P240126,
        demand_hours=[20,21],
        non_hours=[12,17,11,16],
        current_temp=41.2,
        temp_trend=10,
        latest_boost=datetime(2024,1,25, 6,52),
        mock_dt=datetime(2024,1,26,13,2,0)
    )
    assert tt[0] == datetime.max
