from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from custom_components.peaqhvac.service.hvac.ihvac import IHvac

import logging
import time
from abc import ABC, abstractmethod

from peaqevcore.models.hub.hubmember import HubMember

from custom_components.peaqhvac.service.models.enums.demand import Demand

_LOGGER = logging.getLogger(__name__)


class IHeater(ABC):
    _update_interval = 60

    def __init__(self, hvac: IHvac):
        self._demand: Demand = Demand.NoDemand
        self._hvac: IHvac = hvac
        self._control_module: HubMember = HubMember(data_type=bool, initval=False)
        self._latest_update: float = 0

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

    async def async_update_demand(self):
        if time.time() - self._latest_update > self._update_interval:
            self._latest_update = time.time()
            self._demand = await self.async_get_demand()
            if self.control_module:
                await self.async_update_operation()

    @abstractmethod
    async def async_get_demand(self):
        pass

    @abstractmethod
    async def async_update_operation(self):
        pass

    # def compare to heating demand
    # def get current water temp from nibe
    # def turn on waterboost or not
