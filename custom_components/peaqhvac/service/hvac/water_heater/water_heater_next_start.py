from datetime import datetime, timedelta
import logging

from custom_components.peaqhvac.service.hvac.water_heater.models.group import Group
from custom_components.peaqhvac.service.hvac.water_heater.models.next_water_boost_model import NextWaterBoostModel, DEMAND_MINUTES, get_demand
from custom_components.peaqhvac.service.models.enums.group_type import GroupType
from custom_components.peaqhvac.service.models.enums.demand import Demand
from custom_components.peaqhvac.service.models.enums.hvac_presets import HvacPresets



_LOGGER = logging.getLogger(__name__)


class NextWaterBoost:
    def __init__(self, min_price: float = None, non_hours: list[int] = None, demand_hours: list[int] = None):
        self.model = NextWaterBoostModel(min_price=min_price, non_hours_raw=non_hours, demand_hours_raw=demand_hours)

    def next_predicted_demand(
            self,
            prices_today: list,
            prices_tomorrow: list,
            temp: float,
            temp_trend: float,
            target_temp: float,
            preset: HvacPresets = HvacPresets.Normal,
            now_dt=None,
            latest_boost: datetime = None,
    ) -> tuple[datetime, int | None]:
        if len(prices_today) < 1:
            return datetime.max, None
        self.model.update(temp, temp_trend, target_temp, prices_today, prices_tomorrow, preset, now_dt, latest_boost)

        next_start = self.model.latest_calculation
        if self.model.should_update and self.model.initialized:
            next_start, override_demand = self._get_next_start(
                delay_dt=None if self.model.cold_limit == now_dt else self.model.cold_limit
            )
            self.model.latest_calculation = next_start
            self.model.should_update = False
        next_start = datetime.max if not next_start else next_start
        return next_start, override_demand

    def _get_next_start(self, delay_dt=None) -> tuple[datetime, int | None]:
        last_known = self._last_known_price()
        latest_limit = self.model.latest_boost + timedelta(hours=24) if self.model.latest_boost else self.model.now_dt

        if latest_limit < self.model.now_dt and self.model.is_cold:
            """It's been too long since last boost. Boost now."""
            _LOGGER.debug(f"next boost now due to it being more than 24h since last time")
            return self.model.now_dt.replace(
                minute=self._set_minute_start()
            ), None

        next_dt, override_demand = self._calculate_next_start(delay_dt)  # todo: must also use latestboost +24h in this.
        intersecting1 = self._check_intersecting(next_dt, last_known)
        if intersecting1[0] or next_dt == datetime.max:
            _LOGGER.debug(
                f"returning next boost based on intersection of hours. original: {next_dt}, inter: {intersecting1}")
            return intersecting1

        expected_temp = min(self._get_temperature_at_datetime(next_dt), 39)
        retval = min(next_dt, (latest_limit if latest_limit < last_known else datetime.max))
        return self._set_start_dt(
            low_period=0,
            delayed_dt=retval,
            new_demand=self.model.get_demand_minutes(expected_temp)
        ), override_demand

    def _check_intersecting(self, next_dt, last_known) -> tuple[datetime, int | None]:
        intersecting_non_hours = self._intersecting_special_hours(self.model.non_hours, min(next_dt, last_known))
        intersecting_demand_hours = self._intersecting_special_hours(self.model.demand_hours, min(next_dt, last_known))
        if intersecting_demand_hours:
            best_match = self._get_best_match(intersecting_non_hours, intersecting_demand_hours)
            if best_match:
                # print(f"best match: {best_match}")
                expected_temp = min(self._get_temperature_at_datetime(best_match), 39)
                ret = self._set_start_dt(
                    low_period=0,
                    delayed_dt=min(best_match, next_dt),
                    new_demand=self.model.get_demand_minutes(expected_temp)
                    # special demand because demand_hour
                ), self.model.get_demand_minutes(expected_temp)
                if (ret[0] - self.model.latest_boost > timedelta(hours=2) and self.model.current_temp < 50) or ret[0] > self.model.cold_limit:
                    return ret
        return None, None

    @staticmethod
    def _get_best_match(non_hours, demand_hours) -> datetime | None:
        first_demand = min(demand_hours)
        non_hours = [hour.hour for hour in non_hours]
        for hour in range(first_demand.hour - 1, -1, -1):
            if hour not in non_hours:
                if hour - 1 not in non_hours:
                    return first_demand.replace(hour=hour)
        return None

    def _intersecting_special_hours(self, hourslist, next_dt) -> list[datetime]:
        hours_til_boost = self._get_list_of_hours(self.model.now_dt, next_dt)
        intersection = hours_til_boost.intersection(hourslist)
        if not len(intersection):
            return []
        return list(sorted(intersection))

    def _get_temperature_at_datetime(self, target_dt) -> float:
        delay = (target_dt - self.model.now_dt).total_seconds() / 3600
        return self.model.current_temp + (delay * self.model.temp_trend)

    def _get_list_of_hours(self, start_dt: datetime, end_dt: datetime) -> set[datetime]:
        hours = []
        current = start_dt
        end_dt += timedelta(hours=1)  # Include the hour after end_dt
        while current <= end_dt:
            hours.append(current.replace(minute=0, second=0, microsecond=0))
            current += timedelta(hours=1)
        return set(hours)

    def _last_known_price(self) -> datetime:
        try:
            td = timedelta(hours=len(self.model.prices) - 1)
            ret = self.model.now_dt.replace(hour=0, minute=0) + td
            return ret
        except Exception as e:
            _LOGGER.error(
                f"Error on getting last known price with {self.model.now_dt} and len prices {len(self.model.prices)}: {e}")
            return datetime.max

    def _set_minute_start(self, now_dt=None, low_period=0, delayed=False, new_demand: int = None) -> int:
        now_dt = self.model.now_dt if now_dt is None else now_dt
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
        return now_dt.replace(minute=start_minute)

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

    def _values_are_good(self, i, use_floating_mean) -> bool:
        checklist = [i, i + 1, i - 23, i - 24]
        non_hours = [dt.hour for dt in self.model.non_hours]
        return all([
            (self.model.prices[i] < self.model.floating_mean if use_floating_mean else True) or self.model.prices[
                i] < self.model.min_price,
            (self.model.prices[i + 1] < self.model.floating_mean if use_floating_mean else True) or self.model.prices[
                i + 1] < self.model.min_price,
            not any(item in checklist for item in non_hours)
        ])

    def _calculate_next_start(self, delay_dt=None) -> tuple[datetime, int | None]:
        check_dt = (delay_dt if delay_dt else self.model.now_dt).replace(minute=0)
        # print("is cold") if self.model.is_cold else print("is not cold- will be at:", self.model.cold_limit)
        try:
            if self.model.prices[check_dt.hour] < self.model.floating_mean and self.model.is_cold and not any(
                    [
                        check_dt in self.model.non_hours,
                        (check_dt + timedelta(hours=1)) in self.model.non_hours
                    ]
            ):
                """This hour is cheap enough to start"""
                low_period = self._get_low_period()
                return self._set_start_dt(low_period=low_period), None

            if len(self.model.demand_hours):
                loopstart = self.model.now_dt.hour
                use_floating_mean = False
                min_demand_hour = min((hour for hour in self.model.demand_hours if hour > self.model.now_dt),
                                      default=None)
                if min_demand_hour is None:  # If there's no demand hour later today, find the earliest one tomorrow
                    min_demand_hour = min([h + timedelta(hours=24) for h in self.model.demand_hours],
                                          default=self.model.now_dt)
                loopend = min(len(self.model.prices) - 1, int((
                                                                          min_demand_hour - self.model.now_dt).total_seconds() / 3600) + self.model.now_dt.hour)
                override_demand = max(self.model.get_demand_minutes(self.model.current_temp), 26)
            else:
                loopstart = int(
                    (self.model.cold_limit - self.model.now_dt).total_seconds() / 3600) + self.model.now_dt.hour
                loopend = len(self.model.prices) - 1
                use_floating_mean = True
                override_demand = None
            i = self.find_lowest_2hr_combination(loopstart, loopend, use_floating_mean)
            if i:
                return self._set_start_dt_params(i), override_demand
            return datetime.max, None
        except Exception as e:
            _LOGGER.error(f"Error on getting next start: {e}")
            return datetime.max, None

    def find_lowest_2hr_combination(self, start_index: int, end_index: int, use_floating_mean: bool = True) -> int:
        min_sum = float('inf')
        min_start_index = None
        for i in range(start_index, end_index):
            try:
                current_sum = self.model.prices[i] + self.model.prices[i + 1]
                if current_sum < min_sum:
                    if self._values_are_good(i, use_floating_mean):
                        min_sum = current_sum
                        min_start_index = i
                        if self._stop_2hr_combination(i):
                            break
            except IndexError:
                break
        return min_start_index

    def _stop_2hr_combination(self, i: int) -> bool:
        return any([
            self.model.is_cold,
            self.model.cold_limit < (self.model.now_dt.replace(hour=0) + timedelta(hours=i))
        ])

    def _set_start_dt_params(self, i: int) -> datetime:
        delay = (i - self.model.now_dt.hour)
        delayed_dt = self.model.now_dt + timedelta(hours=delay)
        low_period = self._get_low_period(override_dt=delayed_dt)
        expected_temp = self.model.current_temp + (delay * self.model.temp_trend)
        new_demand = max(self.model.get_demand_minutes(expected_temp),
                         DEMAND_MINUTES[self.model.preset][Demand.LowDemand])
        return self._set_start_dt(low_period, delayed_dt, True, new_demand)