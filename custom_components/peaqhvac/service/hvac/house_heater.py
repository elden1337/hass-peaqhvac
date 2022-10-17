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
        if not self.max_price_lower() and not self.peak_lower():
            desired_offset = offsets[datetime.now().hour] - self._get_tempdiff_rounded() - self._get_temp_extremas()
            return Offset.adjust_to_threshold(desired_offset, self._hvac.hub.options.hvac_tolerance)
        return -10

    def peak_lower(self) -> bool:
        """Lower if peaqev prediction is breaching and minute > x"""
        return False

    def max_price_lower(self) -> bool:
        """Temporarily lower to -10 if this hour is maxhour and temp > set-temp + 0.5C"""
        if self._get_tempdiff() >= 0.5:
            return datetime.now().hour == Offset.max_hour_today
        return False

    def _get_tempdiff_rounded(self) -> int:
        return int(self._get_tempdiff()/1.1)

    def _get_tempdiff(self) -> float:
        return self._hvac.hub.sensors.average_temp_indoors.value - self._hvac.hub.sensors.set_temp_indoors

    def _get_temp_extremas(self) -> int:
        count = self._hvac.hub.sensors.average_temp_indoors.sensorscount
        set_temp = self._hvac.hub.sensors.set_temp_indoors
        minval = (self._hvac.hub.sensors.average_temp_indoors.min - set_temp) / count
        maxval = (set_temp - self._hvac.hub.sensors.average_temp_indoors.max) / count
        return int((maxval - minval)/1.3)

    def _get_temp_trend_offset(self) -> float:
        if self._hvac.hub.sensors.temp_trend_outdoors.samples > 1:
            #ok to use
            pass
        if self._hvac.hub.sensors.temp_trend_indoors.samples > 1:
            #ok to use
            pass

    # def compare to water demand
