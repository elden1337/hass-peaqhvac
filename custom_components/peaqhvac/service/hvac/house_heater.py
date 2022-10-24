from custom_components.peaqhvac.service.hvac.iheater import IHeater
from custom_components.peaqhvac.service.models.demand import Demand
from custom_components.peaqhvac.service.hvac.offset import Offset
import custom_components.peaqhvac.extensionmethods as ex
from datetime import datetime
import logging
import time

from custom_components.peaqhvac.service.models.hvacmode import HvacMode

_LOGGER = logging.getLogger(__name__)
UPDATE_INTERVAL = 60
HEATBOOST_TIMER = 7200

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
            if all(
                    [
                        self._get_tempdiff() > 1,
                        self._hvac.hub.sensors.temp_trend_indoors.gradient > 0.5,
                        self._hvac.hub.sensors.temp_trend_outdoors.gradient > 0
                    ]
                ):
                _LOGGER.debug("Preparing to run ventilation-boost based on hot and current temperature rising.")
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
        if dm >= 0:
            return Demand.NoDemand
        if dm > int(_compressor_start / 2):
            return Demand.LowDemand
        if dm > _compressor_start:
            return Demand.MediumDemand
        if dm < _compressor_start:
            return Demand.HighDemand
        else:
            _LOGGER.debug(f"compressor_start is: {_compressor_start} and pushed DM is: {dm}. Could not calculate demand.")
            return Demand.NoDemand

    def get_current_offset(self, offsets:dict) -> int:
        if self.max_price_lower():
            return -10
        else:
            desired_offset = self._set_calculated_offset(offsets)
        if self._should_temp_lower():
            desired_offset -= 1
        return Offset.adjust_to_threshold(desired_offset, self._hvac.hub.options.hvac_tolerance)

    def _set_calculated_offset(self, offsets: dict) -> int:
        ret = ex.subtract(
                offsets[datetime.now().hour],
                self._get_tempdiff_rounded(),
                self._get_temp_extremas()
                #self._get_temp_trend_offset()
             )
        ret = self._add_temp_boost(ret)
        return int(round(ret, 0))

    latest_boost = 0

    def _add_temp_boost(self, preoffset: int) -> int:
        if time.time() - self.latest_boost > HEATBOOST_TIMER:
            if self._hvac.hvac_mode == HvacMode.Idle:
                if self._get_tempdiff() < 0:
                    if self._hvac.hub.sensors.temp_trend_indoors.gradient <= 0.3:
                        """boost +1 since there is no sunwarming and no heating atm"""
                        _LOGGER.debug("adding additional heating since there is no sunwarming happening and house is too cold.")
                        preoffset += 1
                        self.latest_boost = time.time()
        else:
            preoffset += 1
            if self._get_tempdiff() > 1:
                """Turn off the boost prematurely"""
                preoffset -= 1
                self.latest_boost = 0
        return preoffset


    def _should_temp_lower(self) -> bool:
        if self._hvac.hub.sensors.peaqev_installed:
            if 35 <= datetime.now().minute < 50 and self._hvac.hub.sensors.peaqev_facade.above_stop_threshold:
                _LOGGER.debug("Lowering offset because of peak about to be breached.")
                return True
            elif self._hvac.hvac_electrical_addon > 0:
                return True
        return False

    def max_price_lower(self) -> bool:
        """Temporarily lower to -10 if this hour is a peak for today and temp > set-temp + 0.5C"""
        if self._get_tempdiff() >= 0.5:
            return datetime.now().hour in Offset.peaks_today
        return False

    def _get_tempdiff_rounded(self) -> int:
        diff = self._get_tempdiff()
        if diff == 0:
            return 0
        if diff > 0:
            return int(diff/1)
        return int(diff/0.5)

    def _get_tempdiff(self) -> float:
        return self._hvac.hub.sensors.average_temp_indoors.value - self._hvac.hub.sensors.set_temp_indoors

    def _get_temp_extremas(self) -> float:
        count = self._hvac.hub.sensors.average_temp_indoors.sensorscount
        set_temp = self._hvac.hub.sensors.set_temp_indoors
        maxtemp = self._hvac.hub.sensors.average_temp_indoors.max
        mintemp = self._hvac.hub.sensors.average_temp_indoors.min
        minval = (mintemp - set_temp)
        maxval = (maxtemp - set_temp)
        try:
            if maxval < 0 and minval < 0:
                ret = (((set_temp - maxtemp) + (set_temp - mintemp) / 2) * -1)
            elif minval < 0:
                ret = (maxval - minval) / count
            else:
                ret = (((set_temp - maxtemp) + (set_temp - mintemp) / 2) * -1) / (count / 2)
            return round(ret, 2)
        except ZeroDivisionError as e:
            return 0

    def _get_temp_trend_offset(self) -> float:
        try:
            ret = 0
            if self._hvac.hub.sensors.temp_trend_outdoors.is_clean:
                ret = self._hvac.hub.sensors.temp_trend_outdoors.gradient/2 #outdoors is halfed
            if self._hvac.hub.sensors.temp_trend_indoors.is_clean:
                ret += self._hvac.hub.sensors.temp_trend_indoors.gradient
            return round(ret/1.2,2)
        except ZeroDivisionError as e:
            return 0

    # def compare to water demand
    # def calc with prognosis