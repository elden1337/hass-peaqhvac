from datetime import datetime, timedelta
import logging

from custom_components.peaqhvac.service.hvac.water_heater.models.group import Group
from custom_components.peaqhvac.service.hvac.water_heater.models.next_water_boost_model import NextWaterBoostModel, DEMAND_MINUTES, get_demand
from custom_components.peaqhvac.service.models.enums.group_type import GroupType
from custom_components.peaqhvac.service.models.enums.demand import Demand
from custom_components.peaqhvac.service.models.enums.hvac_presets import HvacPresets



_LOGGER = logging.getLogger(__name__)

REQUIRED_DEMAND_DELAY = 6

#--------------------------------

from datetime import datetime, timedelta
from statistics import mean
from dataclasses import dataclass


@dataclass
class PriceData:
    price: float
    price_spread: float
    time: datetime
    water_temp: float
    is_cold: bool
    is_demand: bool
    is_non: bool
    target_temp: int


TARGET_TEMP = 47
MAX_TARGET_TEMP = 53

def _calculate_target_temp_for_hour(temp_at_time: float, is_demand: bool, price: float, price_spread:float, min_price:float) -> int:
    target = TARGET_TEMP if price > min_price else MAX_TARGET_TEMP
    #diff_to_target = int(target - temp_at_time)
    #print(f"diff to target {diff_to_target}, temp at time {temp_at_time}, target {target}")
    if int(target - temp_at_time) <= 0:
        return target

    add_temp = 0
    if price_spread < 0.5:
        add_temp = 20
    elif price_spread < 0.8:
        add_temp = 15
    elif price_spread < 1:
        add_temp = 10

    if is_demand:
        add_temp += 10

    return min(int(temp_at_time+add_temp), target)


def _get_temperature_at_datetime(now_dt, target_dt, current_temp, temp_trend) -> float:
    delay = (target_dt - now_dt).total_seconds() / 3600
    return max(10,round(current_temp + (delay * temp_trend), 1))


def _add_data_list(now_dt: datetime, prices:list, current_temp: float, trend: float, water_limit: float, demand_hours:list, non_hours: list, min_price: float) -> list:
    data = []
    for idx, p in enumerate(prices[now_dt.hour:]):
        new_hour = (now_dt + timedelta(hours=idx)).replace(minute=50, second=0, microsecond=0)
        second_hour = (now_dt + timedelta(hours=idx + 1))
        temp_at_time = _get_temperature_at_datetime(now_dt, new_hour, current_temp, trend)
        data.append(PriceData(
            p,
            round(p / mean(prices[idx:]), 2),
            new_hour,
            temp_at_time,
            temp_at_time <= (water_limit if not second_hour.hour in demand_hours else water_limit +2),
            second_hour.hour in demand_hours,
            new_hour.hour in non_hours or second_hour.hour in non_hours,
            _calculate_target_temp_for_hour(temp_at_time, second_hour.hour in demand_hours, p, round(p / mean(prices[idx:]), 2), min_price)
        )
        )
    return data


def get_next_start(prices: list, demand_hours: list, non_hours: list, current_temp: float, temp_trend: float, min_price: float = 0,
                   latest_boost: datetime = None, mock_dt: datetime = datetime.now()) -> tuple[datetime,float|None]:
    water_limit = 40
    low_water_limit = 15
    now_dt = mock_dt
    trend = -0.5 if -0.5 < temp_trend < 0.1 else temp_trend
    if latest_boost is not None:
        if now_dt - latest_boost < timedelta(hours=1):
            now_dt = now_dt+timedelta(hours=1)
    data = _add_data_list(now_dt, prices, current_temp, trend, water_limit, demand_hours, non_hours, min_price)
    selected: PriceData = None

    for d in data:
        if all([
            d.is_cold,
            (d.price_spread < 1 or (d.is_demand or d.water_temp < low_water_limit)),
            not d.is_non
            ]):
            selected = d
            break
    if selected is None:
        return datetime.max, None

    # cheaper in the vicinity?
    filtered = []
    if selected.is_demand:
        filtered = [d for d in data if d.time-selected.time <= timedelta(hours=-2) and d.time >= now_dt]
    else:
        filtered = [d for d in data if max(d.time, selected.time) - min(d.time, selected.time) <= timedelta(hours=2) and d.time >= now_dt]

    for fdemand in [d for d in filtered if d.is_demand and not d.is_non]:
        if fdemand.is_cold and fdemand.price_spread < selected.price_spread:
            selected = fdemand
            return selected.time, selected.target_temp

    for d in sorted(filtered, key=lambda x: (not x.is_demand, x.price_spread)):
        if not d.is_non and d.price_spread < selected.price_spread and not selected.is_demand and not selected.water_temp < low_water_limit:
            selected = d
            break
    return selected.time, selected.target_temp


#--------------------------------



class NextWaterBoost:
    def __init__(self, min_price: float = None, non_hours: list[int] = [], demand_hours: list[int] = []):
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
            current_dm: int = None,
            debug: bool = False
    ) -> tuple[datetime, int | None]:
        if len(prices_today) < 1:
            return datetime.max, None
        self.model.update(temp, temp_trend, target_temp, prices_today, prices_tomorrow, preset, now_dt, latest_boost)

        if self.model.should_update and self.model.initialized:
            if debug:
                _LOGGER.debug(f"updating next water boost")
            next_start, override_demand = self._get_next_start(
                delay_dt=None if self.model.cold_limit == now_dt else self.model.cold_limit,
                current_dm=current_dm, debug=debug
            )

            next_start = datetime.max if not next_start or self._get_temperature_at_datetime(next_start) > 50 else next_start
            if self._use_new_calculation(self.model.latest_calculation, next_start, self.model.latest_boost, debug):
                self.model.latest_calculation = next_start
                self.model.latest_override_demand = override_demand
                self.model.should_update = False
        return self.model.latest_calculation, self.model.latest_override_demand

    @staticmethod
    def _use_new_calculation(old_calculation: datetime, new_calculation: datetime, latest_boost: datetime = None, debug:bool = False) -> bool:
        latest = latest_boost if latest_boost else datetime.min
        if debug:
            _LOGGER.debug(f"new calculation: {new_calculation}, old calculation: {old_calculation}")
        if old_calculation is None or old_calculation == datetime.max:
            return True
        if new_calculation is None or new_calculation == datetime.max:
            return False
        if old_calculation < latest + timedelta(hours=1):
            """we have just boosted. don't boost again"""
            return True
        if new_calculation == datetime.max and old_calculation == datetime.max:
            return True
        return new_calculation < old_calculation

    def _get_next_start(self, delay_dt=None, current_dm=None, debug=False) -> tuple[datetime, int | None]:
        last_known = self._last_known_price()
        latest_limit = self.model.latest_boost + timedelta(hours=24) if self.model.latest_boost else self.model.now_dt
        if debug:
            _LOGGER.debug(f"last known: {last_known}, latest limit: {latest_limit}")
        if latest_limit < self.model.now_dt and self.model.is_cold:
            """It's been too long since last boost. Boost now."""
            _LOGGER.debug(f"next boost now due to it being more than 24h since last time")
            return self.model.now_dt.replace(
                minute=self._set_minute_start()
            ), None

        delay_dt_check = min(last_known, delay_dt) if delay_dt else None
        next_dt, override_demand = self._calculate_next_start(delay_dt_check, current_dm)  # todo: must also use latestboost +24h in this.
        if debug:
            _LOGGER.debug(f"next boost vanilla: {next_dt}, override demand: {override_demand}")
        intersecting1 = self._check_intersecting(next_dt, last_known, current_dm)
        if intersecting1[0]:
            if debug:
                _LOGGER.debug(f"returning next boost based on intersection of hours. original: {next_dt}, inter: {intersecting1}")
            return intersecting1

        expected_temp = min(self._get_temperature_at_datetime(next_dt), 39)
        retval = min(next_dt, (latest_limit if latest_limit < last_known else datetime.max))
        #print("ex", expected_temp, "at:",next_dt,  self._get_datetime_at_temperature(40))
        if debug:
            _LOGGER.debug(f"returning next boost based on expected temp. original: {next_dt}, expected temp: {expected_temp}")
        return self._set_start_dt(
            delayed_dt=retval,
            new_demand=self.model.get_demand_minutes(expected_temp)
        ), override_demand

    def _check_intersecting(self, next_dt: datetime, last_known: datetime, current_dm) -> tuple[datetime, int | None]:
        intersecting_non_hours = self._intersecting_special_hours(self.model.non_hours, min(next_dt, last_known))
        intersecting_demand_hours = self._intersecting_special_hours(self.model.demand_hours, min(next_dt, last_known))
        if intersecting_demand_hours:
            best_match = self._get_best_match(intersecting_non_hours, intersecting_demand_hours, current_dm)
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

    def _get_best_match(self, non_hours: list[datetime], demand_hours: list[datetime], current_dm) -> datetime | None:
        """even if demand hour intersect we cannot boost more often than every 2 hours if dm are low"""
        try:
            if current_dm and current_dm < -100:
                first_demand = min([d for d in demand_hours if d > self.model.latest_boost + timedelta(hours=2)])
            else:
                first_demand = min([d for d in demand_hours if d > self.model.latest_boost])
        except:
            return None
        non_hours = [hour.hour for hour in non_hours]
        for hour in range(first_demand.hour - 1, -1, -1):
            if hour not in non_hours and hour:
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

    def _get_datetime_at_temperature(self, target_temp: float) -> datetime:
        time_diff = (target_temp - self.model.current_temp) / self.model.temp_trend
        return self.model.now_dt + timedelta(hours=time_diff)

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
        ret = all([
            (self.model.price_dict[i] < self.model.floating_mean if use_floating_mean else True) or
            self.model.price_dict[i] < self.model.min_price,
            (self.model.price_dict[i + timedelta(hours=1)] < self.model.floating_mean if use_floating_mean else True) or
            self.model.price_dict[i + timedelta(hours=1)] < self.model.min_price,
            i not in self.model.non_hours,
            (i + timedelta(hours=1)) not in self.model.non_hours
        ])
        return ret

    def _calculate_next_start(self, delay_dt=None, current_dm=None) -> tuple[datetime, int | None]:
        try:
            check_dt = self.norm_dt(delay_dt if delay_dt else self.model.now_dt)
            current_price = self.model.price_dict.get(check_dt, None)
            if current_price:
                if current_price < self.model.floating_mean and self.model.is_cold and not any(
                        [
                            check_dt in self.model.non_hours,
                            (check_dt + timedelta(hours=1)) in self.model.non_hours,
                            current_dm < -800
                        ]
                ):
                    """This hour is cheap enough to start and it is cold"""

                    return self._set_start_dt(), None
            else:
                _LOGGER.warning(f"Unable to find price for {check_dt} in {self.model.price_dict.keys()}")

            if len(self.model.demand_hours):
                required_delay = self.model.latest_boost + timedelta(hours=REQUIRED_DEMAND_DELAY)
                loopstart = max(self.norm_dt(self.model.now_dt),min(self.norm_dt(self.model.cold_limit), self.norm_dt(required_delay)))
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
            _LOGGER.exception("_calculate_next_start",e)
            return datetime.max, None

    @staticmethod
    def norm_dt(dt: datetime) -> datetime:
        return dt.replace(minute=0, second=0, microsecond=0)

    def find_lowest_2hr_combination(self, start_index: datetime, end_index: datetime,
                                    use_floating_mean: bool = True) -> datetime:
        min_sum = float('inf')
        min_start_index = None
        current: datetime = start_index
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
                _LOGGER.exception("2hr combo", e)
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
