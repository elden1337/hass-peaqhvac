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
        _compressor_start = self._dm_compressor_start if self._dm_compressor_start is not None else -300
        if dm >= 0:
            return Demand.NoDemand
        if dm > int(_compressor_start / 2):
            return Demand.LowDemand
        if dm > _compressor_start:
            return Demand.MediumDemand
        if dm < _compressor_start:
            return Demand.HighDemand


    def get_current_offset(self, offsets:dict) -> int:
        desired_offset = offsets[datetime.now().hour] - int(self._get_tempdiff()) - int(self._get_temp_extremas()/1.3)
        return Offset.adjust_to_threshold(desired_offset, self._hvac.hub.options.hvac_tolerance)

    def _get_tempdiff(self) -> float:
        return self._hvac.hub.sensors.average_temp_indoors.value - self._hvac.hub.sensors.set_temp_indoors

    def _get_temp_extremas(self) -> float:
        count = self._hvac.hub.sensors.average_temp_indoors.sensorscount
        set = self._hvac.hub.sensors.set_temp_indoors
        minval = (self._hvac.hub.sensors.average_temp_indoors.min - set) / count
        maxval = (set - self._hvac.hub.sensors.average_temp_indoors.max) / count
        return maxval - minval

    def _get_temp_trend_offset(self) -> float:
        if self._hvac.hub.sensors.temp_trend_outdoors.samples > 1:
            #ok to use
            pass
        if self._hvac.hub.sensors.temp_trend_indoors.samples > 1:
            #ok to use
            pass


    # def compare to water demand
