from statistics import mean, stdev
from datetime import datetime, timedelta
import logging
from typing import Any

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
        Demand.ErrorDemand:  0,
        Demand.NoDemand:     0,
        Demand.LowDemand:    26,
        Demand.MediumDemand: 34,
        Demand.HighDemand:   46
    },
    HvacPresets.Eco:    {
        Demand.ErrorDemand:  0,
        Demand.NoDemand:     0,
        Demand.LowDemand:    26,
        Demand.MediumDemand: 34,
        Demand.HighDemand:   46
    },
    HvacPresets.Away:   {
        Demand.ErrorDemand:  0,
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
    return Demand.ErrorDemand


from dataclasses import dataclass, field
from datetime import datetime, timedelta


@dataclass
class NextWaterBoostModel:
    prices: list = field(default_factory=lambda: [])
    min_price: float = None  # type: ignore
    groups: list = field(default_factory=lambda: [])
    non_hours: set = field(default_factory=lambda: [])
    demand_hours: set = field(default_factory=lambda: {})
    preset: HvacPresets = HvacPresets.Normal
    now_dt: datetime = None  # type: ignore
    latest_boost: datetime = None  # type: ignore
    floating_mean: float = None  # type: ignore
    temp_trend: float = None  # type: ignore
    current_temp: float = None  # type: ignore
    target_temp: float = None  # type: ignore

    @property
    def cold_limit(self) -> datetime:
        if self.is_cold:
            return self.now_dt
        try:
            hourdiff = (self.current_temp - self.target_temp) / self.temp_trend
        except ZeroDivisionError:
            hourdiff = DELAY_LIMIT
        return self.now_dt + timedelta(hours=hourdiff)

    @property
    def is_cold(self) -> bool:
        return self.current_temp < self.target_temp

    @property
    def demand(self) -> Demand:
        return get_demand(self.current_temp)

    @property
    def demand_minutes(self) -> int:
        return DEMAND_MINUTES[self.preset][self.demand]

    @property
    def price_dt(self) -> dict[datetime, float]:
        ret = {}
        start_dt = self.now_dt.replace(hour=0, minute=0, second=0, microsecond=0)
        for i, price in enumerate(self.prices):
            ret[start_dt + timedelta(hours=i)] = price
        return ret

    def init_vars(self, temp, temp_trend, target_temp, prices_today: list, prices_tomorrow: list, preset: HvacPresets,
                  min_price: float, non_hours: list = None, high_demand_hours: dict = None, now_dt=None,
                  latest_boost: datetime = None) -> None:
        if non_hours is None:
            non_hours = []
        if high_demand_hours is None:
            high_demand_hours = {}
        self.min_price = min_price
        self.prices = prices_today + prices_tomorrow
        self.set_now_dt(now_dt)
        self.latest_boost = latest_boost
        self.non_hours = self._set_hours(non_hours)
        self.demand_hours = self._set_hours(high_demand_hours)
        self.set_floating_mean()
        self._group_prices(prices_today, prices_tomorrow)
        self.preset = preset
        self.temp_trend = DEFAULT_TEMP_TREND if temp_trend > DEFAULT_TEMP_TREND else temp_trend
        self.current_temp = temp
        self.target_temp = target_temp

    def _set_hours(self, input_hours: list) -> set:
        ret = set()
        start_dt = self.now_dt.replace(hour=0, minute=0, second=0, microsecond=0)
        for i in range(0, len(self.prices)):
            if i in input_hours:
                ret.add(start_dt + timedelta(hours=i))
        return ret

    def set_now_dt(self, now_dt=None) -> None:
        self.now_dt = datetime.now() if now_dt is None else now_dt

    def set_floating_mean(self, now_dt=None) -> float:
        self.floating_mean = mean(self.prices[self.now_dt.hour:])

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
                group_type = __set_group_type(mean([self.prices[j] for j in current_group]), len(current_group) == 24,
                                              average)
                continuous_groups.append(Group(group_type, current_group))
                current_group = [i]
        group_type = __set_group_type(mean([self.prices[j] for j in current_group]), len(current_group) == 24, average)
        continuous_groups.append(Group(group_type, current_group))
        self.groups = continuous_groups


class NextWaterBoost:
    """
    make sure to take into account that temp may be way lower than now on calculated start.
    ie, if now is 8am, and it's cold but expensive, the next start may be 8pm but then temp will be lower and may need more demand_minutes.

    if we are approaching a high period, so that next water boost is calculated in approx 8hrs:
    - what will the estimated temperature be of the water in 8hrs?
    - when (if before) do we estimate the temperature to be below threshold?
    - if there are high-demand hours between now and the 8hrs, what will the temperature be for each of those?
	    >- if there is a high-demand hour coming up in let's say 5 hours, what would be the cheapest period from now til then to make sure water is warm enough?

    """

    def __init__(self):
        self.model = NextWaterBoostModel()

    def next_predicted_demand(
            self,
            prices_today: list,
            prices_tomorrow: list,
            min_price: float,
            temp: float,
            temp_trend: float,
            target_temp: float,
            preset: HvacPresets = HvacPresets.Normal,
            now_dt=None,
            non_hours=None,
            high_demand_hours=None,
            latest_boost: datetime = None,
    ) -> datetime:
        if len(prices_today) < 1:
            return datetime.max
        self.model.init_vars(temp, temp_trend, target_temp, prices_today, prices_tomorrow, preset, min_price, non_hours,
                             high_demand_hours, now_dt, latest_boost)

        return self._get_next_start(
            delay_dt=None if self.model.cold_limit == now_dt else self.model.cold_limit
        )

    def _get_next_start(self, delay_dt=None) -> datetime:
        last_known = self._last_known_price()
        latest_limit = self.model.latest_boost + timedelta(hours=24) if self.model.latest_boost else datetime.now()

        if latest_limit < datetime.now() and self.model.is_cold:
            """It's been too long since last boost. Boost now."""
            return datetime.now().replace(
                minute=self._set_minute_start(now_dt=datetime.now()),
                second=0,
                microsecond=0
            )

        # calculate vanilla next start
        next_dt = self._calculate_next_start()

        intersecting_non_hours = self._intersecting_special_hours(self.model.non_hours, next_dt)
        intersecting_demand_hours = self._intersecting_special_hours(self.model.demand_hours, next_dt)

        if intersecting_demand_hours:
            best_match = self._get_best_match(intersecting_non_hours, intersecting_demand_hours)
            if best_match:
                expected_temp = self._get_temperature_at_datetime(best_match)
                return self._set_start_dt(
                    low_period=0,
                    delayed_dt=best_match,
                    new_demand=max(DEMAND_MINUTES[self.model.preset][get_demand(expected_temp)], 24)
                    # special demand because demand_hour
                )

        expected_temp = self._get_temperature_at_datetime(next_dt)
        return self._set_start_dt(
            low_period=0,
            delayed_dt=next_dt,
            new_demand=DEMAND_MINUTES[self.model.preset][get_demand(expected_temp)]
        )

    @staticmethod
    def _get_best_match(non_hours, demand_hours) -> Any | None:
        first_demand = min(demand_hours)
        non_hours = [hour.hour for hour in non_hours]
        for hour in range(first_demand.hour - 1, -1, -1):
            if hour not in non_hours:
                if hour - 1 not in non_hours:
                    return first_demand.replace(hour=hour - 1)
        return None

    def _intersecting_special_hours(self, hourslist, next_dt) -> list[datetime]:
        hours_til_boost = self._get_list_of_hours(self.model.now_dt, next_dt)
        intersection = hours_til_boost.intersection(hourslist)
        if not len(intersection):
            return []
        return list(sorted(intersection))

    # def intersecting_demand_hour(self, next_dt) -> datetime|None:
    #     intersections = self._intersecting_special_hours(self.model.demand_hours, next_dt)
    #     if not len(intersections):
    #         return None
    #     next_intersecting_demand_hour = min(intersections)

    #     new_start_hour = self._find_lowest_consecutive_combination({k:v for k, v in self.model.price_dt.items() if k >= self.model.now_dt and k <= next_intersecting_demand_hour}, 2)
    #     new_demand = get_demand(self._get_temperature_at_datetime(new_start_hour+timedelta(hours=1)))
    #     return self._set_start_dt(low_period=0, delayed_dt=new_start_hour, new_demand=DEMAND_MINUTES[self.model.preset][new_demand], delayed=True)

    def _get_temperature_at_datetime(self, target_dt) -> float:
        delay = (target_dt - self.model.now_dt).total_seconds() / 3600
        return self.model.current_temp + (delay * self.model.temp_trend)

    # def _find_lowest_consecutive_combination(self, hours:dict, n) -> datetime:
    #     min_sum = float('inf')
    #     min_start_index = None
    #     items = list(hours.items())
    #     for i in range(len(items) - n + 1):
    #         current_sum = sum(value for key, value in items[i:i+n])
    #         if current_sum <= min_sum:
    #             min_sum = current_sum
    #             min_start_index = items[i][0]
    #     return min_start_index

    def _get_list_of_hours(self, start_dt: datetime, end_dt: datetime) -> list:
        hours = []
        current = start_dt
        while current <= end_dt:
            hours.append(current.replace(minute=0, second=0, microsecond=0))
            current += timedelta(hours=1)
        return set(hours)

    # def range_not_in_nonhours(self, _next_dt) -> bool:
    #     if _next_dt.hour in self.model.non_hours:
    #         return False
    #     if _next_dt.hour + 1 in self.model.non_hours:
    #         return False
    #     return True

    def _last_known_price(self) -> datetime:
        try:
            last_known_price = self.model.now_dt.replace(hour=0, minute=0, second=0) + timedelta(
                hours=len(self.model.prices) - 1)
            return last_known_price
        except Exception as e:
            _LOGGER.error(
                f"Error on getting last known price with {self.model.now_dt} and len prices {len(self.model.prices)}: {e}")
            return datetime.max

    def _set_minute_start(self, now_dt, low_period=0, delayed=False, new_demand: int = None) -> int:
        demand = new_demand if new_demand is not None else self.model.demand_minutes
        if low_period >= 60 - now_dt.minute and not delayed:
            start_minute = max(now_dt.minute, min(60 - int(demand / 2), 59))
        else:
            start_minute = min(60 - int(demand / 2), 59)
        return start_minute

    def _set_start_dt(self, low_period: int, delayed_dt: datetime = None, delayed: bool = False,
                      new_demand: int = None) -> datetime:
        now_dt = self.model.now_dt if delayed_dt is None else delayed_dt
        start_minute: int = self._set_minute_start(now_dt, low_period, delayed, new_demand)
        return now_dt.replace(minute=start_minute, second=0, microsecond=0)

    def _get_low_period(self, override_dt=None) -> int:
        dt = self.model.now_dt if override_dt is None else override_dt
        if override_dt is not None:
            _start_hour = dt.hour + (int(self.model.now_dt.day != override_dt.day) * 24)
        else:
            _start_hour = dt.hour
        low_period: int = 0
        for i in range(_start_hour, len(self.model.prices)):
            if self.model.prices[i] > self.model.floating_mean:
                break
            if i == dt.hour:
                low_period = 60 - dt.minute
            else:
                low_period += 60
        return low_period

    def _values_are_good(self, i) -> bool:
        checklist = [i, i + 1, i - 23, i - 24]
        non_hours = [dt.hour for dt in self.model.non_hours]
        return all([
            self.model.prices[i] < self.model.floating_mean or self.model.prices[i] < self.model.min_price,
            self.model.prices[i + 1] < self.model.floating_mean or self.model.prices[i + 1] < self.model.min_price,
            not any(item in checklist for item in non_hours)
        ])

    def _calculate_next_start(self) -> datetime:
        try:
            if self.model.prices[self.model.now_dt.hour] < self.model.floating_mean and not any(
                    [self.model.now_dt.hour in self.model.non_hours,
                     self.model.now_dt.hour + 1 in self.model.non_hours]
            ):
                """This hour is cheap enough to start"""
                low_period = self._get_low_period()
                return self._set_start_dt(low_period=low_period)
            print("checking A")
            for i in range(self.model.now_dt.hour, len(self.model.prices) - 1):
                """Search forward for other hours to start"""
                if self._values_are_good(i):
                    return self._set_start_dt_params(i)
        except Exception as e:
            _LOGGER.error(f"Error on getting next start: {e}")
            return datetime.max

    # def _calculate_last_start(self, group: list = []) -> datetime:
    #     try:
    #         _param_i = None
    #         _range = range(self.model.now_dt.hour, min(len(self.model.prices) - 1, self.model.now_dt.hour + HOUR_LIMIT))
    #         if len(group) > 1:
    #             _range = range(self.model.now_dt.hour, max(group))
    #         print("checking B", group)
    #         for i in _range:
    #             if self._values_are_good(i):
    #                 _param_i = i
    #         if _param_i is None:
    #             return self._calculate_last_start_reverse()
    #         return self._set_start_dt_params(_param_i)
    #     except Exception as e:
    #         _LOGGER.error(f"Error on getting last close start: {e}")
    #         return datetime.max

    # def _calculate_last_start_reverse(self):
    #     try:
    #         print("checking C")
    #         for i in reversed(range(self.model.now_dt.hour,min(len(self.model.prices) - 1, self.model.now_dt.hour + HOUR_LIMIT))):
    #             if self._values_are_good(i):
    #                 return self._set_start_dt_params(i)
    #     except Exception as e:
    #         _LOGGER.error(f"Error on getting last start: {e}")
    #         return datetime.max

    def _set_start_dt_params(self, i: int) -> datetime:
        delay = (i - self.model.now_dt.hour)
        delayed_dt = self.model.now_dt + timedelta(hours=delay)
        low_period = self._get_low_period(override_dt=delayed_dt)
        excepted_temp = self.model.current_temp + (delay * self.model.temp_trend)
        new_demand = max(DEMAND_MINUTES[self.model.preset][get_demand(excepted_temp)],
                         DEMAND_MINUTES[self.model.preset][Demand.LowDemand])
        return self._set_start_dt(low_period, delayed_dt, True, new_demand)

    def _find_group(self, index: int) -> Group:
        for group in self.model.groups:
            if index in group.hours:
                return group
        return Group(GroupType.UNKNOWN, [])