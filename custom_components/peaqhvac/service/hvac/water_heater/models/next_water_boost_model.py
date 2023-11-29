from datetime import datetime, timedelta
from dataclasses import dataclass, field
from statistics import stdev, mean

from custom_components.peaqhvac.service.hvac.water_heater.models.group import Group
from custom_components.peaqhvac.service.models.enums.group_type import GroupType
from custom_components.peaqhvac.service.models.enums.demand import Demand
from custom_components.peaqhvac.service.models.enums.hvac_presets import HvacPresets



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
            high_demand_hours = []
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

    def get_demand_minutes(self, expected_temp) -> int:
        return DEMAND_MINUTES[self.preset][get_demand(expected_temp)]

    def _set_hours(self, input_hours: list) -> set:
        ret = set()
        start_dt = self.now_dt.replace(hour=0, minute=0, second=0, microsecond=0)
        for i in range(0, len(self.prices)):
            if i in input_hours:
                ret.add(start_dt + timedelta(hours=i))
        return ret

    def set_now_dt(self, now_dt=None) -> None:
        self.now_dt = datetime.now() if now_dt is None else now_dt

    def set_floating_mean(self, now_dt=None) -> None:
        self.floating_mean = mean(self.prices[self.now_dt.hour:])

    def _group_prices(self, prices_today: list, prices_tomorrow: list) -> None:
        today_len = len(prices_today)
        std_dev = stdev(self.prices)
        average = mean(self.prices)
        std_dev_tomorrow = None
        average_tomorrow = None
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