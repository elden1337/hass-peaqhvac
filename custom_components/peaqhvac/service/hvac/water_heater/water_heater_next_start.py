from statistics import mean, stdev
from datetime import datetime, timedelta
import logging

from custom_components.peaqhvac.service.hvac.water_heater.models.group import Group
from custom_components.peaqhvac.service.models.enums.group_type import GroupType
from custom_components.peaqhvac.service.models.enums.demand import Demand
from custom_components.peaqhvac.service.models.enums.hvac_presets import HvacPresets
from custom_components.peaqhvac.service.hvac.water_heater.const import *


# from enum import Enum

# class GroupType(Enum):
#     LOW = "cheap"
#     MID = "medium"
#     HIGH = "expensive"
#     UNKNOWN = "unknown"
#     FLAT = "flat"

# class Demand(Enum):
#     NoDemand = "No demand"
#     LowDemand = "Low demand"
#     MediumDemand = "Medium demand"
#     HighDemand = "High demand"

# class HvacPresets(Enum):
#     Normal = 1
#     Eco = 2
#     Away = 3
#     ExtendedAway = 4

# class Group:
#     def __init__(self, group_type: GroupType, hours: list[int]):
#         self.group_type = group_type
#         self.hours = hours



_LOGGER = logging.getLogger(__name__)

HOUR_LIMIT = 18
DELAY_LIMIT = 48
MIN_DEMAND = 26
DEFAULT_TEMP_TREND = -0.4


DEMAND_MINUTES = {
    HvacPresets.Normal: {
        Demand.NoDemand:     0,
        Demand.LowDemand:    26,
        Demand.MediumDemand: 35,
        Demand.HighDemand:   45
    },
    HvacPresets.Eco: {
        Demand.NoDemand:     0,
        Demand.LowDemand:    26,
        Demand.MediumDemand: 35,
        Demand.HighDemand:   45
    },
    HvacPresets.Away: {
        Demand.NoDemand:     0,
        Demand.LowDemand:    0,
        Demand.MediumDemand: 26,
        Demand.HighDemand:   26
    }
}

def get_demand(temp) -> Demand:
    if temp is None:
        return Demand.NoDemand
    if 0 < temp < 100:
        if temp >= 40:
            return Demand.NoDemand
        if temp > 35:
            return Demand.LowDemand
        if temp >= 25:
            return Demand.MediumDemand
        if temp < 25:
            return Demand.HighDemand
    return Demand.NoDemand


class NextWaterBoost:
    def __init__(self):
        self.prices = []
        self.min_price: float = None  # type: ignore
        self.groups = []
        self.non_hours: list = []
        self.demand_hours: dict = {}
        self.preset: HvacPresets = HvacPresets.Normal
        self.now_dt: datetime = None  # type: ignore
        self.floating_mean: float = None  # type: ignore
        self.temp_trend: float = None  # type: ignore
        self.current_temp: float = None  # type: ignore

    def next_predicted_demand(
            self,
            prices_today: list,
            prices_tomorrow: list,
            min_price: float,
            temp: float,
            temp_trend: float,
            target_temp: float,
            demand: int = MIN_DEMAND,
            preset: HvacPresets = HvacPresets.Normal,
            now_dt=None,
            non_hours=None,
            high_demand_hours=None
    ) -> datetime:
        if len(prices_today) < 1:
            return datetime.max
        self._init_vars(temp,temp_trend, prices_today, prices_tomorrow, preset, min_price, non_hours, high_demand_hours, now_dt)
        try:
            if target_temp - temp > 0:
                delay = 0
            else:
                delay = (target_temp - temp) / self.temp_trend
        except ZeroDivisionError:
            delay = DELAY_LIMIT
        return self._get_next_start(
            demand=demand,
            delay_dt=None if delay == 0 else self.now_dt + timedelta(hours=delay),
            cold=self.current_temp < 40
        )

    def _init_vars(self, temp, temp_trend, prices_today: list, prices_tomorrow: list, preset: HvacPresets, min_price: float, non_hours: list=None, high_demand_hours: dict=None, now_dt=None) -> None:
        if non_hours is None:
            non_hours = []
        if high_demand_hours is None:
            high_demand_hours = {}
        self.min_price = min_price
        self.prices = prices_today + prices_tomorrow
        self.non_hours = non_hours
        self.demand_hours = high_demand_hours
        self._set_now_dt(now_dt)
        self._set_floating_mean()
        self._group_prices(prices_today, prices_tomorrow)
        self.preset = preset
        self.temp_trend = DEFAULT_TEMP_TREND if temp_trend > DEFAULT_TEMP_TREND else temp_trend
        self.current_temp = temp

    def _get_next_start(self, demand: int, delay_dt=None, cold=True) -> datetime:
        try:
            last_known_price = self.now_dt.replace(hour=0, minute=0, second=0) + timedelta(hours=len(self.prices) - 1)
        except Exception as e:
            _LOGGER.error(
                f"Error on getting last known price with {self.now_dt} and len prices {len(self.prices)}: {e}")
            return datetime.max
        if last_known_price - self.now_dt > timedelta(hours=HOUR_LIMIT) and not cold:
            group = self._find_group(self.now_dt.hour)
            if group.group_type == GroupType.LOW:
                return self._calculate_last_start(demand,group.hours)
            return self._calculate_last_start(demand)
        _next_dt = self._calculate_next_start(demand)
        if not delay_dt:
            if self.range_not_in_nonhours(_next_dt):
                return _next_dt.replace(minute=self._set_minute_start(demand, _next_dt))
            return self._get_next_start(demand, delay_dt=_next_dt+timedelta(hours=1), cold=cold)
        if _next_dt < delay_dt:
            return self._calculate_last_start(demand)
        return _next_dt.replace(minute=self._set_minute_start(demand, _next_dt))

    def range_not_in_nonhours(self, _next_dt) -> bool:
        if _next_dt.hour in self.non_hours:
            return False
        if _next_dt.hour + 1 in self.non_hours:
            return False
        return True

    def _set_now_dt(self, now_dt=None) -> None:
        self.now_dt = datetime.now() if now_dt is None else now_dt

    def _set_floating_mean(self, now_dt=None) -> float:
        self.floating_mean = mean(self.prices[self.now_dt.hour:])

    def _set_minute_start(self, demand, now_dt, low_period = 0, delayed = False) -> int:
        if low_period >= 60 - now_dt.minute and not delayed:
            start_minute = max(now_dt.minute, min(60 - int(demand / 2), 59))
        else:
            start_minute = min(60 - int(demand / 2), 59)
        return start_minute

    def _set_start_dt(self, demand: int, low_period: int, delayed_dt: datetime = None,delayed: bool = False) -> datetime:
        now_dt = self.now_dt if delayed_dt is None else delayed_dt
        start_minute: int = self._set_minute_start(demand, now_dt, low_period, delayed)
        return now_dt.replace(minute=start_minute, second=0, microsecond=0)

    def _get_low_period(self, override_dt=None) -> int:
        dt = self.now_dt if override_dt is None else override_dt
        if override_dt is not None:
            _start_hour = dt.hour + (int(self.now_dt.day != override_dt.day) * 24)
        else:
            _start_hour = dt.hour
        low_period: int = 0
        for i in range(_start_hour, len(self.prices)):
            if self.prices[i] > self.floating_mean:
                break
            if i == dt.hour:
                low_period = 60 - dt.minute
            else:
                low_period += 60
        return low_period

    def _values_are_good(self, i) -> bool:
        return all([
            self.prices[i] < self.floating_mean or self.prices[i] < self.min_price,
            self.prices[i + 1] < self.floating_mean or self.prices[i + 1] < self.min_price,
            [i, i + 1, i - 23, i - 24] not in self.non_hours,
        ])

    def _calculate_next_start(self, demand: int) -> datetime:
        try:
            if self.prices[self.now_dt.hour] < self.floating_mean and not any(
                [self.now_dt.hour in self.non_hours,
                 self.now_dt.hour + 1 in self.non_hours]
                 ):
                """This hour is cheap enough to start"""
                low_period = self._get_low_period()
                return self._set_start_dt(demand=demand, low_period=low_period)
            print("checking A")
            for i in range(self.now_dt.hour, len(self.prices) - 1):
                """Search forward for other hours to start"""
                if self._values_are_good(i):
                    return self._set_start_dt_params(i, demand)
        except Exception as e:
            _LOGGER.error(f"Error on getting next start: {e}")
            return datetime.max

    def _calculate_last_start(self, demand: int, group: list = []) -> datetime:
        try:
            _param_i = None
            _range = range(self.now_dt.hour, min(len(self.prices) - 1, self.now_dt.hour + HOUR_LIMIT))
            if len(group) > 1:
                _range = range(self.now_dt.hour, max(group))
            print("checking B", group)
            for i in _range:
                if self._values_are_good(i):
                    _param_i = i
            if _param_i is None:
                return self._calculate_last_start_reverse(demand)
            return self._set_start_dt_params(_param_i, demand)
        except Exception as e:
            _LOGGER.error(f"Error on getting last close start: {e}")
            return datetime.max

    def _calculate_last_start_reverse(self, demand: int):
        try:
            print("checking C")
            for i in reversed(range(self.now_dt.hour,min(len(self.prices) - 1, self.now_dt.hour + HOUR_LIMIT))):
                if self._values_are_good(i):
                    return self._set_start_dt_params(i, demand)
        except Exception as e:
            _LOGGER.error(f"Error on getting last start: {e}")
            return datetime.max

    def _set_start_dt_params(self, i: int, demand: int) -> datetime:
        delay = (i - self.now_dt.hour)
        delayed_dt = self.now_dt + timedelta(hours=delay)
        low_period = self._get_low_period(override_dt=delayed_dt)
        excepted_temp = self.current_temp + (delay * self.temp_trend)
        new_demand = max(DEMAND_MINUTES[self.preset][get_demand(excepted_temp)],DEMAND_MINUTES[self.preset][Demand.LowDemand])
        return self._set_start_dt(new_demand, low_period, delayed_dt, True)

    def _group_prices(self, prices_today: list, prices_tomorrow: list) -> None:
        today_len = len(prices_today)
        std_dev = stdev(self.prices)
        average = mean(self.prices)
        if len(prices_tomorrow):
            std_dev_tomorrow = stdev(prices_tomorrow)
            average_tomorrow = mean(prices_tomorrow)
        continuous_groups = []
        current_group = [0]

        def __set_group_type(_average, flat, average):
            if flat:
                return GroupType.FLAT
            if _average < average or _average < self.min_price:
                return GroupType.LOW
            elif _average > 1.5 * average:
                return GroupType.HIGH
            else:
                return GroupType.MID

        for i in range(1, len(self.prices)):
            if i == today_len:
                std_dev = std_dev_tomorrow
                average = average_tomorrow
            if abs(self.prices[i] - self.prices[current_group[-1]]) <= std_dev and self.prices[i] not in self.non_hours:
                current_group.append(i)
            else:
                group_type = __set_group_type(mean([self.prices[j] for j in current_group]), len(current_group) == 24, average)
                continuous_groups.append(Group(group_type, current_group))
                current_group = [i]
        group_type = __set_group_type(mean([self.prices[j] for j in current_group]), len(current_group) == 24, average)
        continuous_groups.append(Group(group_type, current_group))
        self.groups = continuous_groups

    def _find_group(self, index: int) -> Group:
        for group in self.groups:
            if index in group.hours:
                return group
        return Group(GroupType.UNKNOWN, [])


#prices = [0.21,0.21,0.21,0.2,0.2,0.19,0.21,0.23,0.24,0.27,0.27,0.27,0.26,0.25,0.25,0.26,0.27,0.28,0.29,0.28,0.27,0.25,0.23,0.21]
# prices = [0.21,0.21,0.21,0.2,0.2,0.19,0.21,0.23,1.24,1.27,1.27,1.27,1.26,1.25,1.25,1.26,1.27,1.28,1.29,1.28,0.27,0.25,0.23,0.21]
# nb = NextWaterBoost()
# demand_hours = {0: [20], 1: [6,7], 3: [7], 4: [22, 23]}

# _dt: datetime = datetime.now().replace(hour=8, minute=48)
# tt2 = nb.next_predicted_demand(prices, [], temp=39.8, temp_trend=0, target_temp=40, now_dt=_dt, demand=26, non_hours=[7, 11, 12, 15, 16, 17], high_demand_hours=demand_hours.get(_dt.weekday(), []))
# tt3 = nb.next_predicted_demand(prices, [], temp=42, temp_trend=-3, target_temp=40, now_dt=_dt, non_hours=[7, 11, 12, 15, 16, 17], high_demand_hours=demand_hours.get(_dt.weekday(), [])) #must have some kind of demand since it will be way too low when reaching next heating.

# print(f"low: {tt2}")
# print(f"not low yet {tt3}")

# for x in nb.groups:
#     print(x.group_type, x.hours)

# prices = [0.24, 0.24, 0.24, 0.24, 0.25, 0.27, 0.31, 1.42, 2.39, 1.84, 1.52, 1.45, 1.44, 1.42, 1.39, 1.42, 1.48, 1.82,
#           2.66, 3.52, 2.85, 2.07, 1.78, 0.29]
# prices_tomorrow = [0.29,0.29,0.28,0.26,0.27,0.26,0.29,0.51,1.95,1.64,0.82,0.51,0.41,0.32,0.31,0.31,0.32,0.33,0.31,0.28,0.26,0.25,0.21,0.17]