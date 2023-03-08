from abc import ABC, abstractmethod
from typing import Tuple

from custom_components.peaqhvac.service.models.enums.demand import Demand
from peaqevcore.models.hub.hubmember import HubMember
import logging
import time

_LOGGER = logging.getLogger(__name__)

class IHeater(ABC):
    _update_interval = 60

    def __init__(self, hvac):
        self._demand = Demand.NoDemand
        self._hvac = hvac
        self._control_module = HubMember(data_type=bool, initval=False)
        self._latest_update = 0

    @property
    @abstractmethod
    def is_initialized(self) -> bool:
        pass

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
        if time.time() - self._latest_update > self._update_interval:
            self._latest_update = time.time()
            self._demand = self._get_demand()
            if self.control_module:
                self.update_operation()

    @abstractmethod
    def _get_demand(self):
        pass

    @abstractmethod
    def update_operation(self):
        pass

    # def compare to heating demand
    # def get current water temp from nibe
    # def turn on waterboost or not
