from abc import abstractmethod

from custom_components.peaqhvac.service.models.enums.demand import Demand
from peaqevcore.models.hub.hubmember import HubMember
import logging
import time

_LOGGER = logging.getLogger(__name__)

UPDATE_INTERVAL = 60

class IHeater:
    def __init__(self, hvac):
        self._demand = Demand.NoDemand
        self._hvac = hvac
        self._control_module = HubMember(data_type=bool, initval=False)
        self._latest_update = 0

    @property
    def demand(self) -> Demand:
        if self._demand is not None:
            return self._demand
        _LOGGER.error(f"{__name__} had no value for Demand.")
        return Demand.NoDemand

    @property
    def control_module(self) -> bool:
        return self._control_module.value

    @control_module.setter
    def control_module(self, val) -> None:
        self._control_module.value = val

    def _get_demand_for_current_hour(self) -> Demand:
        # if vacation or similar, return NoDemand
        pass

    def update_demand(self):
        if time.time() - self._latest_update > UPDATE_INTERVAL:
            self._latest_update = time.time()
            self._demand = self._get_demand()
            if self.control_module:
                self._update_operation()

    @abstractmethod
    def _get_demand(self):
        pass

    @abstractmethod
    def _update_operation(self):
        pass

    # def compare to heating demand
    # def get current water temp from nibe
    # def turn on waterboost or not



    # #househeater
    # def update_demand(self):
    #     """this function will be the most complex in this class. add more as we go"""
    #     if time.time() - self._latest_update > UPDATE_INTERVAL:
    #         self._latest_update = time.time()
    #         self._demand = self._get_dm_demand(self._hvac.hvac_dm)
    #
    # def _get_dm_demand(self, dm: int) -> Demand:
    #     _compressor_start = self._dm_compressor_start if self._dm_compressor_start is not None else -300
    #     _return_temp = self._hvac.delta_return_temp if self._hvac.delta_return_temp is not None else 1000
    #     if dm >= 0 or _return_temp < 0:
    #         return Demand.NoDemand
    #     if dm > int(_compressor_start / 2):
    #         return Demand.LowDemand
    #     if dm > _compressor_start:
    #         return Demand.MediumDemand
    #     if dm <= _compressor_start:
    #         return Demand.HighDemand
    #     else:
    #         _LOGGER.debug(
    #             f"Compressor_start: {_compressor_start}, delta-return: {self._hvac.delta_return_temp} and pushed DM: {dm}. Could not calculate demand.")
    #         return Demand.NoDemand
    #
    # #waterheater
    # def update_demand(self):
    #     """this function will be the most complex in this class. add more as we go"""
    #     if time.time() - self._latest_update > UPDATE_INTERVAL:
    #         self._latest_update = time.time()
    #         self._demand = self._get_deg_demand()
    #         if self.control_module:
    #             self._update_water_heater_operation()
    #
    # def _update_water_heater_operation(self):
    #     if self.is_initialized:
    #         if self._hvac.hub.sensors.set_temp_indoors.preset == HvacPresets.Normal:
    #             self._set_water_heater_operation_home()
    #         elif self._hvac.hub.sensors.set_temp_indoors.preset == HvacPresets.Away:
    #             self._set_water_heater_operation_away()