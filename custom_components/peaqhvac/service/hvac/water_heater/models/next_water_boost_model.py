from datetime import datetime, timedelta
from statistics import mean

from custom_components.peaqhvac.service.hvac.water_heater.models.water_boost_data import WaterBoostData
from custom_components.peaqhvac.service.models.enums.demand import Demand
from custom_components.peaqhvac.service.models.enums.hvac_presets import HvacPresets

HOUR_LIMIT = 18
DELAY_LIMIT = 48
MIN_DEMAND = 26
DEFAULT_TEMP_TREND = -0.5

DEMAND_MINUTES = {
    HvacPresets.Normal: {
        Demand.ErrorDemand:  0,
        Demand.NoDemand:     0,
        Demand.LowDemand:    20,
        Demand.MediumDemand: 26,
        Demand.HighDemand:   32
    },
    HvacPresets.Eco:    {
        Demand.ErrorDemand:  0,
        Demand.NoDemand:     0,
        Demand.LowDemand:    20,
        Demand.MediumDemand: 24,
        Demand.HighDemand:   28
    },
    HvacPresets.Away:   {
        Demand.ErrorDemand:  0,
        Demand.NoDemand:     0,
        Demand.LowDemand:    0,
        Demand.MediumDemand: 20,
        Demand.HighDemand:   20
    }
}

def get_demand(temp) -> Demand:
    if temp is None:
        return Demand.NoDemand
    if temp > 70 or temp == 0:
        return Demand.ErrorDemand
    if temp >= 40:
        return Demand.NoDemand
    if temp > 35:
        return Demand.LowDemand
    if temp >= 25:
        return Demand.MediumDemand
    if temp < 25:
        return Demand.HighDemand
    return Demand.ErrorDemand

class NextWaterBoostModel:
    def __init__(self, data: WaterBoostData):
        self.data = data

    @property
    def cold_limit(self) -> datetime:
        if self.is_cold:
            return self.data.now_dt
        try:
            hour_diff = (self.data.current_temp - self.data.target_temp) / -self.data.temp_trend
        except ZeroDivisionError:
            hour_diff = DELAY_LIMIT
        return max(self.data.now_dt + timedelta(hours=hour_diff), self.data.now_dt)

    @property
    def is_cold(self) -> bool:
        return self.data.current_temp < self.data.target_temp

    @property
    def demand(self) -> Demand:
        return get_demand(self.data.current_temp)

    @property
    def demand_minutes(self) -> int:
        return DEMAND_MINUTES[self.data.preset][self.demand]

    @property
    def now_dt(self) -> datetime:
        return self.data.now_dt.replace(second=0, microsecond=0) if self.data.now_dt else None

    def _create_price_dict(self, prices) -> dict:
        startofday = self.now_dt.replace(hour=0, minute=0)
        return {startofday + timedelta(hours=i): prices[i] for i in range(0, len(prices))}

    def update(self, temp, temp_trend, target_temp, prices_today: list, prices_tomorrow: list, preset: HvacPresets,
               now_dt=None, latest_boost: datetime = None) -> None:
        _old_dt = self.now_dt
        self.set_now_dt(now_dt)
        new_price_dict = self._create_price_dict(prices_today + prices_tomorrow)
        if new_price_dict != self.data.price_dict:
            if all([
                any([k for k in new_price_dict.keys() if k.date() != self.now_dt.date()]),
                not any([k for k in self.data.price_dict.keys() if k.date() != self.now_dt.date()])
            ]):
                self.data.latest_calculation = None
            self.data.price_dict = new_price_dict
            self.data.should_update = True
        new_non_hours = self._set_hours(self.data.non_hours_raw, preset)
        new_demand_hours = self._set_hours(self.data.demand_hours_raw, preset)
        new_temp_trend = DEFAULT_TEMP_TREND if temp_trend > DEFAULT_TEMP_TREND else temp_trend

        if any([
            _old_dt.hour != self.now_dt.hour,
            self.data.latest_boost != latest_boost,
            self.data.non_hours != new_non_hours,
            self.data.demand_hours != new_demand_hours,
            self.data.preset != preset,
            self.data.temp_trend != new_temp_trend,
            self.data.current_temp != temp,
            self.data.target_temp != target_temp
        ]) and not self.data.should_update:
            self.data.should_update = True

        self.data.latest_boost = latest_boost
        self.data.non_hours = new_non_hours
        self.data.demand_hours = new_demand_hours
        self.set_floating_mean()
        self.data.preset = preset
        self.data.temp_trend = new_temp_trend
        self.data.current_temp = temp
        self.data.target_temp = target_temp
        self.data.initialized = True

    def get_demand_minutes(self, expected_temp) -> int:
        return DEMAND_MINUTES[self.data.preset][get_demand(expected_temp)]

    def _set_hours(self, input_hours: list, preset: HvacPresets) -> set:
        if preset == HvacPresets.Away:
            return set()
        return {k for k in self.data.price_dict.keys() if k.hour in input_hours}

    def set_now_dt(self, now_dt=None) -> None:
        self.data.now_dt = now_dt or datetime.now()

    def set_floating_mean(self) -> None:
        self.data.floating_mean = mean([v for k, v in self.data.price_dict.items() if k >= self.now_dt]) * 0.9