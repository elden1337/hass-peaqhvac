import logging
import time
from datetime import datetime
import custom_components.peaqhvac.extensionmethods as ex
from custom_components.peaqhvac.service.hub.trend import Gradient
from custom_components.peaqhvac.service.hvac import peakfinder
from custom_components.peaqhvac.service.hvac.iheater import IHeater
from custom_components.peaqhvac.service.models.demand import Demand
from dataclasses import dataclass

_LOGGER = logging.getLogger(__name__)
UPDATE_INTERVAL = 60
DEFAULT_WATER_BOOST = 120


@dataclass
class WaterBoosterModel:
    heat_water: bool = False
    heat_water_timer: int = 0
    heat_water_timer_timeout = DEFAULT_WATER_BOOST
    pre_heating: bool = False
    boost: bool = False
    water_is_heating: bool = False


class WaterHeater(IHeater):
    def __init__(self, hvac):
        self._hvac = hvac
        super().__init__(hvac=hvac)
        self._current_temp = 0
        self._latest_update = 0
        self._water_temp_trend = Gradient(max_age=18000, max_samples=10)
        self.booster_model = WaterBoosterModel()

    @property
    def temperature_trend(self) -> float:
        """returns the current temp_trend in C/hour"""
        return self._water_temp_trend.gradient

    @property
    def latest_boost_call(self) -> str:
        """For Lovelace-purposes. Converts and returns epoch-timer to readable datetime-string"""
        if self.booster_model.heat_water_timer > 0:
            return ex.dt_from_epoch(self.booster_model.heat_water_timer)
        return "-"

    @latest_boost_call.setter
    def latest_boost_call(self, val):
        self._latest_update = val

    @property
    def current_temperature(self) -> float:
        """The current reported water-temperature in the hvac"""
        return self._current_temp

    @current_temperature.setter
    def current_temperature(self, val):
        try:
            if self._current_temp != float(val):
                self._current_temp = float(val)
                self._water_temp_trend.add_reading(val=float(val), t=time.time())
                # _LOGGER.debug(f"Added reading {val} to water temp trend")
                self._update_water_heater_operation()
        except ValueError as E:
            _LOGGER.warning(f"unable to set {val} as watertemperature. {E}")
            self.booster_model.heat_water = False

    @IHeater.demand.setter
    def demand(self, val):
        self._demand = val

    @property
    def heat_water(self) -> bool:
        """Returns true if we should try and heat the water"""
        return self.booster_model.heat_water

    @property
    def water_heating(self) -> bool:
        """Return true if the water is currently being heated"""
        return self.temperature_trend > 0 or self.booster_model.pre_heating is True

    def update_demand(self):
        """this function will be the most complex in this class. add more as we go"""
        if time.time() - self._latest_update > UPDATE_INTERVAL:
            self._latest_update = time.time()
            self._demand = self._get_deg_demand()
            self._update_water_heater_operation()

    def _get_deg_demand(self) -> Demand:
        temp = self.current_temperature
        if 0 < temp < 100:
            if temp >= 42:
                return Demand.NoDemand
            if temp > 35:
                return Demand.LowDemand
            if temp >= 25:
                return Demand.MediumDemand
            if temp < 25:
                return Demand.HighDemand
        return Demand.NoDemand

    def _get_water_peak(self, hour: int) -> bool:
        try:
            _prices = []
            _prices.extend(self._hvac.hub.nordpool.prices)
            if self._hvac.hub.nordpool.prices_tomorrow is not None:
                _prices.extend([p for p in self._hvac.hub.nordpool.prices_tomorrow if isinstance(p, (float, int))])
            _neg_prices = [p * -1 for p in _prices]
            peaks = peakfinder.identify_peaks(_neg_prices)
            return _neg_prices[hour] in peaks
        except:
            _LOGGER.debug("Could not calc peak water hours")
            return False

    def _update_water_heater_operation(self):
        """this function updates the heat-water property based on various logic for hourly price, peak level, presence and current water temp"""
        # turn on if reversed_degree_demand >= current_temp
        # turn off after x time to not do a full boost
        # sometimes do a full boost
        is_cheapest = self._get_water_peak(datetime.now().hour)
        if is_cheapest:
            _LOGGER.debug("current hour is identified as a good hour to boost water")

        match self.demand:
            case Demand.HighDemand:
                self.pre_heat()
            case Demand.MediumDemand:
                self.pre_heat()
            case Demand.LowDemand:
                if is_cheapest:
                    self.pre_heat()
            case Demand.NoDemand:
                if is_cheapest:
                    self.pre_heat()

        # ideally we want to wait til the last trimester of a period before commencing the boost or pre-heat to not push peak.

    def pre_heat(self):
        """preheat to regular temp first"""
        self.booster_model.pre_heating = True
        self._toggle_boost()

    def _toggle_boost(self, timer_timeout: int = None):
        if self.booster_model.heat_water:
            if self.booster_model.heat_water_timer_timeout > 0:
                if time.time() - self.booster_model.heat_water_timer > self.booster_model.heat_water_timer_timeout:
                    self.booster_model.heat_water = False
        elif self.booster_model.pre_heating or self.booster_model.boost:
            self.booster_model.heat_water = True
            self.booster_model.heat_water_timer = time.time()
            self.booster_model.heat_water_timer_timeout = timer_timeout if timer_timeout is not None else DEFAULT_WATER_BOOST
