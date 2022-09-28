from custom_components.peaqhvac.service.hvac.iheater import IHeater
from custom_components.peaqhvac.service.models.demand import Demand
from custom_components.peaqhvac.service.hvac.offset import Offset
from datetime import datetime
import logging
import time

_LOGGER = logging.getLogger(__name__)
UPDATE_INTERVAL = 60

class HouseHeater(IHeater):
    def __init__(self, hvac):
        self._degree_minutes = 0
        self._latest_update = 0
        self._hvac = hvac
        self._dm_compressor_start = hvac.hvac_compressor_start
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
        _compressor_start = self._dm_compressor_start
        match dm:
            case _ if dm >= 0:
                return Demand.NoDemand
            case _ if dm > int(_compressor_start/2):
                return Demand.LowDemand
            case _ if dm > _compressor_start:
                return Demand.MediumDemand
            case _ if dm < _compressor_start*2:
                return Demand.HighDemand
            case _:
                _LOGGER.warn(f"Could not get DM from hvac-system. Setting {Demand.NoDemand.name} for heating.")
                return Demand.NoDemand

    def get_current_offset(self, offsets:dict) -> int:
        desired_offset = offsets[datetime.now().hour] - int(self._get_tempdiff()/2)
        return Offset.adjust_to_threshold(desired_offset, self._hvac._hub.options.hvac_tolerance)

    def _get_tempdiff(self) -> float:
        return self._hvac._hub.sensors.average_temp_indoors.value - self._hvac._hub.sensors.set_temp_indoors

    def _get_temp_extremes(self) -> (float, float):
        return self._hvac_hub.sensors.average_temp_indoors.min, self._hvac._hub.sensors.average_temp_indoors.max

    # def compare to water demand
