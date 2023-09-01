import pytest
from datetime import datetime
from custom_components.peaqhvac.service.hvac.water_heater.water_heater_next_start import NextWaterBoost

P230830 = [0.76,0.57,0.59,0.64,0.97,1.5,1.97,2.22,2.16,1.93,1.72,1.55,1.53,1.5,1.48,1.52,1.5,1.79,2.16,2.59,2.58,2.08,1.81,1.43]
P230831 = [1.42,0.8,0.61,0.59,0.6,1.4,1.64,2.17,1.97,1.77,1.51,1.44,1.41,1.38,1.36,1.37,1.4,1.55,1.84,2.28,2.14,1.94,1.62,1.47]
P230901 = [0.38,0.37,0.36,0.36,0.36,0.37,0.4,1.17,1.95,1.69,1.56,1.47,1.41,0.5,0.47,0.52,0.53,0.55,0.55,0.52,0.47,0.43,0.4,0.38]
MIN_DEMAND = 26

def test_start_time_water_is_cold():
    prices = P230830 + P230831
    now_dt = datetime(2023,8,26,18,43,0)
    wb = NextWaterBoost()
    tt = wb.get_next_start(prices=prices, demand=80, now_dt=now_dt)
    assert tt == datetime(2023, 8, 26, 23, 20, 0)

def test_delayed_start_water_not_cooling():
    prices = P230830 + P230831
    now_dt = datetime(2023,8,26,18,43,0)
    wb = NextWaterBoost()
    tt = wb.next_predicted_demand(prices=prices, min_demand=MIN_DEMAND, temp=50, temp_trend=0,target_temp=40, now_dt=now_dt)
    assert tt == datetime(2023, 8, 27, 11, 47, 0)

def test_delayed_start_expensive_single_day():
    now_dt = datetime(2023,8,31,12,29,0)
    wb = NextWaterBoost()
    tt = wb.next_predicted_demand(prices=P230831, min_demand=MIN_DEMAND, temp=47.3, temp_trend=0, target_temp=40, now_dt=now_dt)
    assert tt == datetime(2023,8,31,16,47,0)

def test_delayed_start_expensive():
    prices = P230830 + P230831
    now_dt = datetime(2023,8,30,23,5,0)
    wb = NextWaterBoost()
    tt = wb.next_predicted_demand(prices=prices, min_demand=MIN_DEMAND, temp=46.6, temp_trend=-0.9, target_temp=40, now_dt=now_dt)
    assert tt == datetime(2023,8,31,4,47,0)

def test_get_next_start_real_dt():
    wb = NextWaterBoost()
    tt = wb.get_next_start(prices=P230830 + P230831, demand=MIN_DEMAND)
    assert tt.minute == 47

def test_water_warm_should_heat_later():
    wb = NextWaterBoost()
    now_dt = datetime(2023, 9, 1, 9, 9, 0)
    tt = wb.next_predicted_demand(prices=P230901, min_demand=MIN_DEMAND, temp=52.3, temp_trend=-0.2, target_temp=40, now_dt=now_dt)
    assert tt == datetime(2023,9,1,22,47,0)