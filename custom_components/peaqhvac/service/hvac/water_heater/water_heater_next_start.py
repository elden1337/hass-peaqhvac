from statistics import mean, stdev
from datetime import datetime, timedelta
import logging

from custom_components.peaqhvac.service.hvac.water_heater.models.group import Group
from custom_components.peaqhvac.service.hvac.water_heater.models.group_type import GroupType

_LOGGER = logging.getLogger(__name__)

HOUR_LIMIT = 18
DELAY_LIMIT = 48


class NextWaterBoost:
    def __init__(self):
        self.prices = []
        self.groups = []
        self.non_hours: list = []
        self.now_dt: datetime = None  # type: ignore
        self.floating_mean: float = None  # type: ignore

    def next_predicted_demand(
            self,
            prices_today: list,
            prices_tomorrow: list,
            min_demand: int,
            temp: float,
            temp_trend: float,
            target_temp: float,
            now_dt=None,
            non_hours=[]
    ) -> datetime:
        self._init_vars(prices_today, prices_tomorrow, non_hours, now_dt)
        try:
            delay = (target_temp - temp) / temp_trend
        except ZeroDivisionError:
            delay = DELAY_LIMIT
        return self.get_next_start(
            prices_today=prices_today, prices_tomorrow=prices_tomorrow,
            demand=min_demand,
            non_hours=non_hours,
            now_dt=self.now_dt,
            delay_dt=self.now_dt + timedelta(hours=delay),
            cold=False
        )

    def get_next_start(self, prices_today: list,
            prices_tomorrow: list, demand: int, non_hours=None, now_dt=None, delay_dt=None,
                       cold=True) -> datetime:
        if non_hours is None:
            non_hours = []
        self._init_vars(prices_today, prices_tomorrow, non_hours, now_dt)
        try:
            last_known_price = self.now_dt.replace(hour=0, minute=0, second=0) + timedelta(hours=len(self.prices) - 1)
        except Exception as e:
            _LOGGER.error(
                f"Error on getting last known price with {self.now_dt} and len prices {len(self.prices)}: {e}")
            return datetime.max
        if last_known_price - self.now_dt > timedelta(hours=18) and not cold:
            print("case A")
            group = self._find_group(self.now_dt.hour)
            if group.group_type == GroupType.LOW:
                return self._calculate_last_start(demand, group.hours)
            return self._calculate_last_start(demand)
        _next_dt = self._calculate_next_start(demand)
        if not delay_dt:
            print("case B")
            return _next_dt
        if _next_dt < delay_dt:
            print("case C")
            return self._calculate_last_start(demand)
        print("case D")
        return _next_dt

    def _init_vars(self, prices_today: list, prices_tomorrow: list, non_hours: list, now_dt=None) -> None:
        self.prices = prices_today + prices_tomorrow
        self.non_hours = non_hours
        self._set_now_dt(now_dt)
        self._set_floating_mean()
        self._group_prices(prices_today, prices_tomorrow)

    def _set_now_dt(self, now_dt=None) -> None:
        self.now_dt = datetime.now() if now_dt is None else now_dt

    def _set_floating_mean(self, now_dt=None) -> float:
        self.floating_mean = mean(self.prices[self.now_dt.hour:])

    def _set_start_dt(self, demand: int, low_period: int, delayed_dt: datetime = None,
                      delayed: bool = False) -> datetime:
        now_dt = self.now_dt if delayed_dt is None else delayed_dt
        start_minute: int = now_dt.minute
        if low_period >= 60 - now_dt.minute:
            """delayed start"""
            if not delayed:
                start_minute = max(now_dt.minute, min(60 - int(demand / 2), 59))
            else:
                start_minute = min(60 - int(demand / 2), 59)
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
            self.prices[i] < self.floating_mean,
            self.prices[i + 1] < self.floating_mean,
            [i, i + 1, i - 23, i - 24] not in self.non_hours,
        ])

    def _calculate_next_start(self, demand: int) -> datetime:
        try:
            if self.prices[self.now_dt.hour] < self.floating_mean:
                """This hour is cheap enough to start"""
                low_period = self._get_low_period()
                return self._set_start_dt(demand=demand, low_period=low_period)
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
            for i in reversed(range(self.now_dt.hour,
                                    min(len(self.prices) - 1, self.now_dt.hour + HOUR_LIMIT))):
                if self._values_are_good(i):
                    return self._set_start_dt_params(i, demand)
        except Exception as e:
            _LOGGER.error(f"Error on getting last start: {e}")
            return datetime.max

    def _set_start_dt_params(self, i: int, demand: int) -> datetime:
        delay = (i - self.now_dt.hour)
        delayed_dt = self.now_dt + timedelta(hours=delay)
        low_period = self._get_low_period(override_dt=delayed_dt)
        return self._set_start_dt(demand, low_period, delayed_dt, True)

    def _group_prices(self, prices_today: list, prices_tomorrow: list) -> None:
        today_len = len(prices_today)
        std_dev = stdev(self.prices)
        if len(prices_tomorrow):
            std_dev_tomorrow = stdev(prices_tomorrow)
        continuous_groups = []
        current_group = [0]

        def __set_group_type(_average, _stddev):
            if _average < _stddev:
                return GroupType.LOW
            elif _average > 2 * _stddev:
                return GroupType.HIGH
            else:
                return GroupType.MID

        for i in range(1, len(self.prices)):
            if i == today_len:
                std_dev = std_dev_tomorrow
            if abs(self.prices[i] - self.prices[current_group[-1]]) <= std_dev and self.prices[i] not in self.non_hours:
                current_group.append(i)
            else:
                group_type = __set_group_type(mean([self.prices[j] for j in current_group]), std_dev)
                continuous_groups.append(Group(group_type, current_group))
                current_group = [i]
        group_type = __set_group_type(mean([self.prices[j] for j in current_group]), std_dev)
        continuous_groups.append(Group(group_type, current_group))
        self.groups = continuous_groups

    def _find_group(self, index: int) -> Group:
        for group in self.groups:
            if index in group.hours:
                return group
        return Group(GroupType.UNKNOWN, [])


# prices = [0.24, 0.24, 0.24, 0.24, 0.25, 0.27, 0.31, 1.42, 2.39, 1.84, 1.52, 1.45, 1.44, 1.42, 1.39, 1.42, 1.48, 1.82,
#           2.66, 3.52, 2.85, 2.07, 1.78, 0.29]
# prices_tomorrow = [0.29,0.29,0.28,0.26,0.27,0.26,0.29,0.51,1.95,1.64,0.82,0.51,0.41,0.32,0.31,0.31,0.32,0.33,0.31,0.28,0.26,0.25,0.21,0.17]
# nwb = NextWaterBoost()
# tt = nwb.next_predicted_demand(prices, prices_tomorrow, min_demand=26, temp=42, temp_trend=0, target_temp=40,
#                                now_dt=datetime.now().replace(hour=2, minute=23))#, non_hours=[7, 11, 12, 15, 16, 17])
# print(tt)
# for x in nwb.groups:
#     print(x.group_type, x.hours)
# # # 5:47
