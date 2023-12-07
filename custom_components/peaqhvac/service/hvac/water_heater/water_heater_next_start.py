from datetime import datetime, timedelta
import logging

from custom_components.peaqhvac.service.hvac.water_heater.models.group import Group
from custom_components.peaqhvac.service.hvac.water_heater.models.next_water_boost_model import NextWaterBoostModel, DEMAND_MINUTES, get_demand
from custom_components.peaqhvac.service.models.enums.group_type import GroupType
from custom_components.peaqhvac.service.models.enums.demand import Demand
from custom_components.peaqhvac.service.models.enums.hvac_presets import HvacPresets



_LOGGER = logging.getLogger(__name__)

REQUIRED_DEMAND_DELAY = 6


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
            current_dm: int = None
    ) -> tuple[datetime, int | None]:
        if len(prices_today) < 1:
            return datetime.max, None
        self.model.update(temp, temp_trend, target_temp, prices_today, prices_tomorrow, preset, now_dt, latest_boost)

        next_start = self.model.latest_calculation
        override_demand = self.model.latest_override_demand
        if self.model.should_update and self.model.initialized:
            next_start, override_demand = self._get_next_start(
                delay_dt=None if self.model.cold_limit == now_dt else self.model.cold_limit,
                current_dm=current_dm
            )
            self.model.latest_calculation = next_start
            self.model.latest_override_demand = override_demand
            self.model.should_update = False
        next_start = datetime.max if not next_start or self.model.current_temp > 50 else next_start
        return next_start, override_demand

    def _get_next_start(self, delay_dt=None, current_dm=None) -> tuple[datetime, int | None]:
        last_known = self._last_known_price()
        latest_limit = self.model.latest_boost + timedelta(hours=24) if self.model.latest_boost else self.model.now_dt

        if latest_limit < self.model.now_dt and self.model.is_cold:
            """It's been too long since last boost. Boost now."""
            _LOGGER.debug(f"next boost now due to it being more than 24h since last time")
            return self.model.now_dt.replace(
                minute=self._set_minute_start()
            ), None

        next_dt, override_demand = self._calculate_next_start(delay_dt, current_dm)  # todo: must also use latestboost +24h in this.
        intersecting1 = self._check_intersecting(next_dt, last_known)
        if intersecting1[0] or next_dt == datetime.max:
            # _LOGGER.debug(f"returning next boost based on intersection of hours. original: {next_dt}, inter: {intersecting1}")
            return intersecting1
        expected_temp = min(self._get_temperature_at_datetime(next_dt), 39)
        retval = min(next_dt, (latest_limit if latest_limit < last_known else datetime.max))
        return self._set_start_dt(
            delayed_dt=retval,
            new_demand=self.model.get_demand_minutes(expected_temp)
        ), override_demand

    def _check_intersecting(self, next_dt: datetime, last_known: datetime) -> tuple[datetime, int | None]:
        intersecting_non_hours = self._intersecting_special_hours(self.model.non_hours, min(next_dt, last_known))
        intersecting_demand_hours = self._intersecting_special_hours(self.model.demand_hours, min(next_dt, last_known))
        if intersecting_demand_hours:
            best_match = self._get_best_match(intersecting_non_hours, intersecting_demand_hours)
            if best_match:
                # print(f"best match: {best_match}")
                expected_temp = min(self._get_temperature_at_datetime(best_match), 39)
                ret = self._set_start_dt(
                    delayed_dt=min(best_match, next_dt),
                    new_demand=self.model.get_demand_minutes(expected_temp)
                    # special demand because demand_hour
                ), self.model.get_demand_minutes(expected_temp)
                if (ret[0] - self.model.latest_boost > timedelta(
                        hours=REQUIRED_DEMAND_DELAY) and self.model.current_temp < 50) or ret[
                    0] > self.model.cold_limit:
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
            return max(self.model.price_dict.keys())
        except Exception as e:
            _LOGGER.error(
                f"Error on getting last known price with {self.model.now_dt} and len prices {len(self.model.price_dict.items())}: {e}")
            return datetime.max

    def _set_minute_start(self, now_dt=None, new_demand: int = None) -> int:
        now_dt = self.model.now_dt if now_dt is None else now_dt
        demand = new_demand if new_demand is not None else self.model.demand_minutes
        return min(60 - int(demand / 2), 59)

    def _set_start_dt(self, delayed_dt: datetime = None, delayed: bool = False, new_demand: int = None) -> datetime:
        now_dt = self.model.now_dt if delayed_dt is None else delayed_dt
        start_minute: int = self._set_minute_start(now_dt, new_demand)
        return now_dt.replace(minute=start_minute)

    def _values_are_good(self, i: datetime, use_floating_mean: bool) -> bool:
        return all([
            (self.model.price_dict[i] < self.model.floating_mean if use_floating_mean else True) or
            self.model.price_dict[i] < self.model.min_price,
            (self.model.price_dict[i + timedelta(hours=1)] < self.model.floating_mean if use_floating_mean else True) or
            self.model.price_dict[i + timedelta(hours=1)] < self.model.min_price,
            i not in self.model.non_hours,
            (i + timedelta(hours=1)) not in self.model.non_hours
        ])

    def _calculate_next_start(self, delay_dt=None, current_dm=None) -> tuple[datetime, int | None]:
        check_dt = self.norm_dt(delay_dt if delay_dt else self.model.now_dt)
        try:
            if self.model.price_dict[check_dt] < self.model.floating_mean and self.model.is_cold and not any(
                    [
                        check_dt in self.model.non_hours,
                        (check_dt + timedelta(hours=1)) in self.model.non_hours,
                        current_dm < -600
                    ]
            ):
                """This hour is cheap enough to start and it is cold"""
                return self._set_start_dt(), None

            if len(self.model.demand_hours):
                required_delay = self.model.latest_boost + timedelta(hours=REQUIRED_DEMAND_DELAY)
                loopstart = max(self.model.now_dt,
                                min(self.norm_dt(self.model.cold_limit), self.norm_dt(required_delay)))
                use_floating_mean = False
                min_demand_hour = min(
                    (hour for hour in self.model.demand_hours if hour > max(loopstart, self.model.cold_limit)),
                    default=None)
                if min_demand_hour is None:  # If there's no demand hour later today, find the earliest one tomorrow
                    min_demand_hour = min([h + timedelta(hours=24) for h in self.model.demand_hours],
                                          default=self.model.now_dt)
                loopend = min(max(self.model.price_dict.keys()), min_demand_hour + timedelta(hours=-1))
                override_demand = max(self.model.get_demand_minutes(self.model.current_temp), 26)
            else:
                """start looping when we expect it to be cold"""
                loopstart = self.norm_dt(self.model.cold_limit)
                loopend = max(self.model.price_dict.keys())
                use_floating_mean = True
                override_demand = None
            i = self.find_lowest_2hr_combination(loopstart, loopend, use_floating_mean)
            if i:
                return self._set_start_dt_params(i), override_demand
            return datetime.max, None
        except Exception as e:
            print(e)
            return datetime.max, None

    @staticmethod
    def norm_dt(dt: datetime) -> datetime:
        return dt.replace(minute=0, second=0, microsecond=0)

    def find_lowest_2hr_combination(self, start_index: datetime, end_index: datetime,
                                    use_floating_mean: bool = True) -> datetime:
        min_sum = float('inf')
        min_start_index = None
        current: datetime = start_index
        print(start_index, end_index)
        while current < end_index:
            try:
                current_sum = self.model.price_dict[current] + self.model.price_dict[current + timedelta(hours=1)]
                if current_sum < min_sum:
                    if self._values_are_good(current, use_floating_mean):
                        min_sum = current_sum
                        min_start_index = current
                        if self._stop_2hr_combination(current):
                            break
                current += timedelta(hours=1)
            except Exception as e:
                print("2hr combo", e)
                break
        return min_start_index

    def _stop_2hr_combination(self, i: datetime) -> bool:
        return any([
            self.model.is_cold,
            self.model.cold_limit < i
        ])

    def _set_start_dt_params(self, i: datetime) -> datetime:
        delay = (i - self.model.now_dt) / timedelta(hours=1)
        delayed_dt = self.model.now_dt + timedelta(hours=delay)
        expected_temp = self.model.current_temp + (delay * self.model.temp_trend)
        new_demand = max(self.model.get_demand_minutes(expected_temp),
                         DEMAND_MINUTES[self.model.preset][Demand.LowDemand])
        return self._set_start_dt(delayed_dt, True, new_demand)
