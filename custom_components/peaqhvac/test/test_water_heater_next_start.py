import pytest
from datetime import datetime, timedelta
from ..service.hvac.water_heater.water_heater_next_start import NextWaterBoost
from ..service.models.enums.hvac_presets import HvacPresets

P230830 = [0.76,0.57,0.59,0.64,0.97,1.5,1.97,2.22,2.16,1.93,1.72,1.55,1.53,1.5,1.48,1.52,1.5,1.79,2.16,2.59,2.58,2.08,1.81,1.43]
P230831 = [1.42,0.8,0.61,0.59,0.6,1.4,1.64,2.17,1.97,1.77,1.51,1.44,1.41,1.38,1.36,1.37,1.4,1.55,1.84,2.28,2.14,1.94,1.62,1.47]
P230901 = [0.38,0.37,0.36,0.36,0.36,0.37,0.4,1.17,1.95,1.69,1.56,1.47,1.41,0.5,0.47,0.52,0.53,0.55,0.55,0.52,0.47,0.43,0.4,0.38]
P230902=[0.36,0.35,0.34,0.33,0.33,0.32,0.35,0.37,0.37,0.38,0.38,0.38,0.37,0.37,0.37,0.38,0.4,0.43,0.44,0.45,0.45,0.43,0.4,0.39]
P230903=[0.37,0.37,0.36,0.36,0.37,0.37,0.37,0.39,0.41,0.42,0.44,0.44,0.39,0.25,0.15,0.31,0.45,0.45,0.44,0.42,0.37,0.32,0.22,0.1]
P231214 =[1.17,1.15,1.16,1.16,1.19,1.24,1.47,1.81,1.97,2.19,2.19,1.92,1.81,1.99,2.19,2.73,2.73,2.63,2.11,1.81,1.62,1.43,1.41,1.28]
P231215 =[1.28,1.24,1.2,1.15,1.13,1.2,1.42,1.57,1.78,1.72,1.61,1.51,1.39,1.31,1.28,1.3,1.42,1.37,1.26,1.19,1.15,1.14,0.93,1.05]
MIN_DEMAND = 26

# def test_start_time_water_is_cold_no_non_hours():
#     now_dt = datetime(2023,8,26,18,43,0)
#     wb = NextWaterBoost()
#     tt = wb.next_predicted_demand(prices_today=P230830, prices_tomorrow=P230831, temp=35, temp_trend=0, target_temp=40, preset=HvacPresets.Normal, now_dt=now_dt, latest_boost=now_dt-timedelta(hours=1))
#     assert tt[0] == datetime(2023, 8, 26, 23, 47, 0)
#
#
# def test_start_time_water_is_cold_blocked_by_non_hours():
#     now_dt = datetime(2023,8,26,18,43,0)
#     wb = NextWaterBoost(non_hours=[23])
#     tt = wb.next_predicted_demand(prices_today=P230830, prices_tomorrow=P230831, temp=35, temp_trend=0, target_temp=40, preset=HvacPresets.Normal, now_dt=now_dt, latest_boost=now_dt-timedelta(hours=1))
#     assert tt[0] == datetime(2023, 8, 27, 0, 47, 0)
#
#
# def test_start_time_water_not_cold_no_non_hours():
#     now_dt = datetime(2023,8,26,18,43,0)
#     wb = NextWaterBoost()
#     tt = wb.next_predicted_demand(prices_today=P230830, prices_tomorrow=P230831, temp=44, temp_trend=0, target_temp=40, preset=HvacPresets.Normal, now_dt=now_dt, latest_boost=now_dt-timedelta(hours=1))
#     assert tt[0] == datetime(2023, 8, 27, 3, 50, 0)
#
#
# def test_start_time_water_not_cold_blocked_by_non_hours():
#     now_dt = datetime(2023,8,26,18,43,0)
#     wb = NextWaterBoost(non_hours=[2,3])
#     tt = wb.next_predicted_demand(prices_today=P230830, prices_tomorrow=P230831, temp=44, temp_trend=0, target_temp=40, preset=HvacPresets.Normal, now_dt=now_dt, latest_boost=now_dt-timedelta(hours=1))
#     assert tt[0] == datetime(2023, 8, 27, 4, 50, 0)
#
# def test_start_time_water_demand_hour_dont_start_directly():
#     now_dt = datetime(2023,8,26,19,50,0)
#     wb = NextWaterBoost(non_hours=[2,3],demand_hours=[20,21])
#     tt = wb.next_predicted_demand(prices_today=P231214, prices_tomorrow=P231215, temp=49, temp_trend=0, target_temp=40, preset=HvacPresets.Normal, now_dt=now_dt, latest_boost=now_dt-timedelta(minutes=12))
#     assert tt[0] > now_dt + timedelta(minutes=48)
