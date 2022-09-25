from datetime import datetime
import logging
from custom_components.peaqhvac.service.hvac.iheater import IHeater
from custom_components.peaqhvac.service.models.demand import Demand

class WaterDemandObj:
    days: dict[int, dict[int, Demand]]
    #make this a pattern instead, dict will be clumpsy

_LOGGER = logging.getLogger(__name__)


class WaterHeater(IHeater):
    def __init__(self, hvac):
        self._hvac = hvac
        super().__init__(hvac=hvac)
        self._current_temp = 0

    @property
    def current_temperature(self) -> float:
        return self._current_temp

    @current_temperature.setter
    def current_temperature(self, val):
        try:
            self._current_temp = float(val)
        except:
            _LOGGER.warning(f"unable to set {val} as watertemperature")

    def _get_demand_temperature(self, input: Demand) -> int:
        _demandlimits = {
            Demand.HighDemand: 40,
            Demand.MediumDemand: 30,
            Demand.LowDemand: 25,
            Demand.NoDemand: 15
        }
        return _demandlimits[input]

    # def compare to heating demand
    # def get current water temp from nibe
    # def turn on waterboost or not

