from datetime import datetime, timedelta
from dataclasses import dataclass, field
from statistics import stdev, mean

# from custom_components.peaqhvac.service.hvac.water_heater.models.group import Group
# from custom_components.peaqhvac.service.models.enums.group_type import GroupType
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

from dataclasses import dataclass, field
from datetime import datetime, timedelta

@dataclass
class NextWaterBoostModel:
    min_price: float = None  # type: ignore
    non_hours_raw: list[int] = field(default_factory=lambda: [], repr=False, compare=False)
    demand_hours_raw: list[int] = field(default_factory=lambda: [], repr=False, compare=False)
    initialized: bool = False
    price_dict:dict = field(default_factory=lambda: {})
    preset: HvacPresets = HvacPresets.Normal
    _now_dt: datetime = None  # type: ignore
    latest_boost: datetime = None  # type: ignore

    temp_trend: float = DEFAULT_TEMP_TREND  # type: ignore
    current_temp: float = None  # type: ignore
    target_temp: float = None  # type: ignore

    floating_mean: float = field(default=None, init=False)
    non_hours: set = field(default_factory=lambda: [], init=False)
    demand_hours: set = field(default_factory=lambda: {}, init=False)

    latest_calculation: datetime = field(default=None, init=False)
    latest_override_demand: int = field(default=None, init=False)
    should_update: bool = field(default=True, init=False)

    def __post_init__(self):
        self._now_dt = datetime.now() if self.now_dt is None else self.now_dt
        self.latest_boost = self.now_dt if self.latest_boost is None else self.latest_boost
        self.min_price = -float('inf') if self.min_price is None else self.min_price

    @property
    def cold_limit(self) -> datetime:
        if self.is_cold:
            return self.now_dt
        try:
            hourdiff = (self.current_temp - self.target_temp) / -self.temp_trend
        except ZeroDivisionError:
            hourdiff = DELAY_LIMIT
        return max(self.now_dt + timedelta(hours=hourdiff), self._now_dt)

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
    def now_dt(self) -> datetime:
        return self._now_dt.replace(second=0, microsecond=0) if self._now_dt else None

    def _create_price_dict(self, prices) -> dict:
        startofday = self.now_dt.replace(hour=0, minute=0)
        return {startofday + timedelta(hours=i): prices[i] for i in range(0, len(prices))}

    def update(self, temp, temp_trend, target_temp, prices_today: list, prices_tomorrow: list, preset: HvacPresets,
                  now_dt=None, latest_boost: datetime = None) -> None:
        _old_dt = self.now_dt
        self.set_now_dt(now_dt)
        new_price_dict = self._create_price_dict(prices_today + prices_tomorrow)
        if new_price_dict != self.price_dict:
            if all([
                any([k for k in new_price_dict.keys() if k.date() != self.now_dt.date()]),
                not any([k for k in self.price_dict.keys() if k.date() != self.now_dt.date()])
            ]):
                self.latest_calculation = None
            self.price_dict = new_price_dict
            self.should_update = True
        new_non_hours = self._set_hours(self.non_hours_raw, preset)
        new_demand_hours = self._set_hours(self.demand_hours_raw, preset)
        new_temp_trend = DEFAULT_TEMP_TREND if temp_trend > DEFAULT_TEMP_TREND else temp_trend

        if any([
            _old_dt.hour != self.now_dt.hour,
            self.latest_boost != latest_boost,
            self.non_hours != new_non_hours,
            self.demand_hours != new_demand_hours,
            self.preset != preset,
            self.temp_trend != new_temp_trend,
            self.current_temp != temp,
            self.target_temp != target_temp
        ]) and not self.should_update:
            self.should_update = True

        self.latest_boost = latest_boost
        self.non_hours = new_non_hours
        self.demand_hours = new_demand_hours
        self.set_floating_mean()
        self.preset = preset
        self.temp_trend = new_temp_trend
        self.current_temp = temp
        self.target_temp = target_temp
        self.initialized = True

    def get_demand_minutes(self, expected_temp) -> int:
        return DEMAND_MINUTES[self.preset][get_demand(expected_temp)]

    def _set_hours(self, input_hours: list, preset: HvacPresets) -> set:
        if preset == HvacPresets.Away:
            return set()
        return {k for k in self.price_dict.keys() if k.hour in input_hours}

    def set_now_dt(self, now_dt=None) -> None:
        self._now_dt = datetime.now() if now_dt is None else now_dt

    def set_floating_mean(self, now_dt=None) -> None:
        self.floating_mean = mean([v for k,v in self.price_dict.items() if k >=self.now_dt])*0.9