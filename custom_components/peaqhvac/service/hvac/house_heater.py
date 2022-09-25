from custom_components.peaqhvac.service.hvac.iheater import IHeater
from custom_components.peaqhvac.service.models.demand import Demand
import logging
import time

_LOGGER = logging.getLogger(__name__)
UPDATE_INTERVAL = 60

class HouseHeater(IHeater):
    def __init__(self, hvac):
        self._degree_minutes = 0
        self._latest_update = 0
        self._hvac = hvac
        super().__init__(hvac=hvac)

    @IHeater.demand.setter
    def demand(self, val):
        self._demand = val

    def update_demand(self):
        """this function will be the most complex in this class. add more as we go"""
        if time.time() - self._latest_update > UPDATE_INTERVAL:
            self._latest_update = time.time()
            self._demand = self._get_dm_demand(self._hvac.hvac_dm)

    def _get_dm_demand(self, dm:int) -> Demand:
        match dm:
            case _ if dm > 0:
                return Demand.NoDemand
            case _ if 0 < dm < 100:
                return Demand.LowDemand
            case _ if 100 < dm < 500:
                return Demand.MediumDemand
            case _ if dm < 500:
                return Demand.HighDemand
            case _:
                _LOGGER.warn(f"Could not get DM from hvac-system. Setting {Demand.NoDemand.name} for heating.")
                return Demand.NoDemand

    # def compare to water demand

