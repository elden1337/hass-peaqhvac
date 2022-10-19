from custom_components.peaqhvac.service.hvac.iheater import IHeater
from custom_components.peaqhvac.service.models.demand import Demand
from custom_components.peaqhvac.service.hvac.offset import Offset
import custom_components.peaqhvac.extensionmethods as ex
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

    @property
    def vent_boost(self) -> bool:
        if self._hvac.hub.sensors.temp_trend_indoors.is_clean:
            if self._get_tempdiff() > 1 and self._hvac.hub.sensors.temp_trend_indoors.gradient > 0.5:
                _LOGGER.debug("Preparing to run ventilation-boost based on current temperature rising.")
                return True
            elif self._hvac.hvac_dm <= -700:
                _LOGGER.debug("Preparing to run ventilation-boost based on low degree minutes.")
                return True
        return False

    def update_demand(self):
        """this function will be the most complex in this class. add more as we go"""
        if time.time() - self._latest_update > UPDATE_INTERVAL:
            self._latest_update = time.time()
            self._demand = self._get_dm_demand(self._hvac.hvac_dm)

    def _get_dm_demand(self, dm:int) -> Demand:
        _compressor_start = self._dm_compressor_start if self._dm_compressor_start is not None else -300
        #_LOGGER.debug(f"compressor_start is: {_compressor_start} and pushed DM is: {dm}")
        if dm >= 0:
            return Demand.NoDemand
        if dm > int(_compressor_start / 2):
            return Demand.LowDemand
        if dm > _compressor_start:
            return Demand.MediumDemand
        if dm < _compressor_start:
            return Demand.HighDemand

    def get_current_offset(self, offsets:dict) -> int:
        if self.max_price_lower():
            return -10
        if self.peak_lower():
            desired_offset = -5
        else:
            desired_offset = ex.subtract(
                offsets[datetime.now().hour],
                self._get_tempdiff_rounded(),
                self._get_temp_extremas()
                #self._get_temp_trend_offset()
             )
        return Offset.adjust_to_threshold(desired_offset, self._hvac.hub.options.hvac_tolerance)

    def peak_lower(self) -> bool:
        """Lower if peaqev prediction is breaching and minute > x"""
        if self._hvac.hub.sensors.peaqev_installed:
            if datetime.now().minute >= 40 and self._hvac.hub.sensors.peaqev_facade.above_stop_threshold:
                _LOGGER.debug("Lowering offset because of peak about to be breached.")
                return True
        return False

    def max_price_lower(self) -> bool:
        """Temporarily lower to -10 if this hour is maxhour and temp > set-temp + 0.5C"""
        if self._get_tempdiff() >= 0.5:
            return datetime.now().hour == Offset.max_hour_today
        return False

    def _get_tempdiff_rounded(self) -> int:
        diff = self._get_tempdiff()
        if diff == 0:
            return 0
        if diff > 0:
            return int(diff/1.1)
        return int(diff/0.7)

    def _get_tempdiff(self) -> float:
        return self._hvac.hub.sensors.average_temp_indoors.value - self._hvac.hub.sensors.set_temp_indoors

    def _get_temp_extremas(self) -> int:
        count = self._hvac.hub.sensors.average_temp_indoors.sensorscount
        set_temp = self._hvac.hub.sensors.set_temp_indoors
        minval = (self._hvac.hub.sensors.average_temp_indoors.min - set_temp) / count
        maxval = (set_temp - self._hvac.hub.sensors.average_temp_indoors.max) / count
        return int((maxval - minval)/1.3)

    def _get_temp_trend_offset(self) -> float:
        ret = 0
        if self._hvac.hub.sensors.temp_trend_outdoors.is_clean:
            ret = self._hvac.hub.sensors.temp_trend_outdoors.gradient
        if self._hvac.hub.sensors.temp_trend_indoors.is_clean:
            ret += self._hvac.hub.sensors.temp_trend_indoors.gradient
        return (ret*-1)/3

    # def compare to water demand
    # def calc with prognosis