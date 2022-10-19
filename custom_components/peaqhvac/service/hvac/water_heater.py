import logging
from custom_components.peaqhvac.service.hvac.iheater import IHeater
from custom_components.peaqhvac.service.models.demand import Demand
import time


class WaterDemandObj:
    days: dict[int, dict[int, Demand]]
    #make this a pattern instead, dict will be clumpsy

_LOGGER = logging.getLogger(__name__)
UPDATE_INTERVAL = 60

class WaterHeater(IHeater):
    def __init__(self, hvac):
        self._hvac = hvac
        super().__init__(hvac=hvac)
        self._current_temp = 0
        self._latest_update = 0

    @property
    def current_temperature(self) -> float:
        return self._current_temp

    @current_temperature.setter
    def current_temperature(self, val):
        try:
            self._current_temp = float(val)
        except:
            _LOGGER.warning(f"unable to set {val} as watertemperature")

    @IHeater.demand.setter
    def demand(self, val):
        self._demand = val

    def update_demand(self):
        """this function will be the most complex in this class. add more as we go"""
        if time.time() - self._latest_update > UPDATE_INTERVAL:
            self._latest_update = time.time()
            self._demand = self._get_dm_demand(self._hvac.hvac_watertemp)

    @property
    def water_boost(self) -> bool:
        return False

    def _get_dm_demand(self, temp: int) -> Demand:
        if temp >= 45:
            return Demand.NoDemand
        if temp > 35:
            return Demand.LowDemand
        if temp > 30:
            return Demand.MediumDemand
        if temp < 20:
            return Demand.HighDemand

    def _get_demand_thresholds(self, input: Demand) -> int:
        _demandlimits = {
            Demand.HighDemand: 40,
            Demand.MediumDemand: 30,
            Demand.LowDemand: 25,
            Demand.NoDemand: 15
        }
        return _demandlimits[input]

    #check threshold if available

    # def compare to heating demand
    # def get current water temp from nibe
    # def turn on waterboost or not

