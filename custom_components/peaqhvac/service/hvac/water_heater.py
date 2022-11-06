"""th hsad"""
import logging
import time
import custom_components.peaqhvac.extensionmethods as ex
from custom_components.peaqhvac.service.hub.trend import Gradient
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
        if self.booster_model.heat_water_timer > 0:
            return ex.dt_from_epoch(self.booster_model.heat_water_timer)
        return "-"

    @latest_boost_call.setter
    def latest_boost_call(self, val):
        self._latest_update = val

    @property
    def current_temperature(self) -> float:
        return self._current_temp

    @current_temperature.setter
    def current_temperature(self, val):
        try:
            self._current_temp = float(val)
            self._water_temp_trend.add_reading(val=float(val), t=time.time())
            _LOGGER.debug(f"Added reading {val} to water temp trend")
            self._update_water_heater_operation()
        except:
            _LOGGER.warning(f"unable to set {val} as watertemperature")
            self.booster_model.heat_water = False

    @IHeater.demand.setter
    def demand(self, val):
        self._demand = val

    @property
    def heat_water(self) -> bool:
        return self.booster_model.heat_water

    @property
    def water_heating(self) -> bool:
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
            if temp >= 45:
                return Demand.NoDemand
            if temp > 40:
                return Demand.LowDemand
            if temp > 30:
                return Demand.MediumDemand
            if temp < 20:
                return Demand.HighDemand
        return Demand.NoDemand

    def _update_water_heater_operation(self):
        """this function updates the heat-water property based on various logic for hourly price, peak level, presence and current water temp"""
        # turn on if reversed_degree_demand >= current_temp
        # turn off after x time to not do a full boost
        # sometimes do a full boost

        match self.demand:
            case Demand.HighDemand:
                self.pre_heat()
            case Demand.MediumDemand:
                self.pre_heat()
            case Demand.LowDemand:
                # do
                pass
            case Demand.NoDemand:
                # do
                pass
        #ideally we want to wait til the last trimester of a period before commencing the boost or pre-heat to not push peak.
        pass


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
