import logging
from datetime import datetime, timedelta
from statistics import mean
from dataclasses import dataclass

from custom_components.peaqhvac.service.models.enums.hvac_presets import HvacPresets


_LOGGER = logging.getLogger(__name__)

REQUIRED_DEMAND_DELAY = 6


@dataclass  # pylint: disable=too-many-instance-attributes
class PriceData:
    price: float
    price_spread: float
    time: datetime
    water_temp: float
    is_cold: bool
    is_demand: bool
    is_non: bool
    target_temp: int


@dataclass  # pylint: disable=too-many-instance-attributes
class NextStartPostModel:
    prices: list
    demand_hours: list
    non_hours: list
    current_temp: float
    temp_trend: float
    min_price: float = 0
    hvac_preset: HvacPresets = HvacPresets.Normal
    latest_boost: datetime|None = None
    dt: datetime = datetime.now()

    def __post_init__(self):
        self.temp_trend = -0.5 if -0.5 < self.temp_trend < 0.1 else self.temp_trend


@dataclass
class NextStartExportModel:
    next_start: datetime
    target_temp: int | None


TARGET_TEMP = 47
MAX_TARGET_TEMP = 53


class NextWaterBoost:
    def __init__(self):
        self.water_limit: float = 40
        self.low_water_limit: float = 20
        self.min_price: float = 0
        self.dt: datetime = datetime.now()

    def get_next_start(self, model: NextStartPostModel) -> NextStartExportModel:
        self.water_limit = 30 if model.hvac_preset == HvacPresets.Away else 40
        self.low_water_limit = self.water_limit - 20
        
        self.dt = model.dt
        self.min_price = model.min_price
        data = self.get_data(model)
        selected = self.get_selected(data)
        if selected is None:
            return NextStartExportModel(datetime.max, None)
        filtered = self.get_filtered(data, selected)
        selected = self.get_final_selected(filtered, selected)
        return NextStartExportModel(selected.time, selected.target_temp)

    @staticmethod
    def _calculate_target_temp_for_hour(temp_at_time: float, is_demand: bool, price: float, price_spread:float, min_price:float) -> int:
        target = TARGET_TEMP if price > min_price else MAX_TARGET_TEMP
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

    @staticmethod
    def _get_temperature_at_datetime(now_dt, target_dt, current_temp, temp_trend) -> float:
        delay = (target_dt - now_dt).total_seconds() / 3600
        return max(10, round(current_temp + (delay * temp_trend), 1))

    def _add_data_list(self, model: NextStartPostModel) -> list:
        data = []
        for idx, p in enumerate(model.prices[self.dt.hour:], start=self.dt.hour):
            new_hour = (self.dt + timedelta(hours=idx - self.dt.hour)).replace(minute=50, second=0, microsecond=0)
            second_hour = (self.dt + timedelta(hours=idx - self.dt.hour + 1))
            temp_at_time = self._get_temperature_at_datetime(self.dt, new_hour, model.current_temp, model.temp_trend)
            if new_hour < self.reset_hour(self.dt):
                continue
            data.append(PriceData(
                p,
                round(p / mean(model.prices[idx - self.dt.hour:]), 2),
                new_hour,
                temp_at_time,
                self._calculate_is_cold(temp_at_time, second_hour, model, p,
                                        model.prices[idx + 1] if idx + 1 < len(model.prices) else 9999),
                second_hour.hour in model.demand_hours,
                new_hour.hour in model.non_hours or second_hour.hour in model.non_hours,
                self._calculate_target_temp_for_hour(temp_at_time, second_hour.hour in model.demand_hours, p,
                                                     round(p / mean(model.prices[idx - self.dt.hour:]), 2),
                                                     model.min_price)
            ))
        return data

    def _calculate_is_cold(self, temp_at_time: float, second_hour: datetime, model: NextStartPostModel, p: float, p2: float) -> bool:
        calculated_water_limit = self.water_limit
        if p < model.min_price and p2 < self.min_price:
            return temp_at_time <= calculated_water_limit+5
        if second_hour.hour in model.demand_hours:
            return temp_at_time <= calculated_water_limit+2
        return temp_at_time <= calculated_water_limit


    def reset_hour(self, dt) -> datetime:
        return dt.replace(minute=0,second=0,microsecond=0)

    def get_data(self, model: NextStartPostModel) -> list:
        if model.latest_boost is not None:
            if self.dt - model.latest_boost < timedelta(hours=1):
                self.dt = self.dt+timedelta(hours=1)
        data = self._add_data_list(model)
        return data

    def get_selected(self, data: list) -> PriceData:
        selected: PriceData = None
        for d in data:
            if all([
                d.is_cold,
                (d.price_spread < 1 or d.price < self.min_price or (d.is_demand or d.water_temp < d.target_temp)),
                not d.is_non,
                d.time >= self.reset_hour(self.dt)
                ]):
                selected = d
                break
        return selected

    def get_filtered(self, data: list, selected: PriceData) -> list:
        return [d for d in data if max(d.time, selected.time) - min(d.time, selected.time) <= timedelta(hours=2) and d.time >= self.reset_hour(self.dt)]

    def get_final_selected(self, filtered: list, selected: PriceData) -> PriceData:
        for fdemand in [d for d in filtered if d.is_demand and not d.is_non]:
            if fdemand.is_cold and fdemand.price_spread < selected.price_spread:
                selected = fdemand
                _LOGGER.debug("final selected chose a demandhour", selected)
                return selected

        for d in sorted(filtered, key=lambda x: (not x.is_demand, x.price_spread)):
            if not d.is_non and d.price_spread < selected.price_spread and not selected.is_demand and not selected.water_temp < self.low_water_limit:
                selected = d
                break
        return selected
