from abc import abstractmethod
import logging
from custom_components.peaqhvac.service.hvac.offset import Offset
from custom_components.peaqhvac.service.models.demand import Demand
from homeassistant.core import (
    HomeAssistant
)
from custom_components.peaqhvac.service.models.hvacoperations import HvacOperations

_LOGGER = logging.getLogger(__name__)


class IHvac:
    waterdemand: Demand = Demand.NoDemand
    hvacdemand: Demand = Demand.NoDemand
    current_offset: int = 0

    def __init__(self, hass: HomeAssistant, hub):
        self._hub = hub
        self._hass = hass

    @property
    @abstractmethod
    def hvac_offset(self) -> int:
         pass

    def get_offset(self) -> bool:
        ret = Offset.getoffset(
            self._hub.options.hvac_tolerance,
            self._hub.nordpool.prices,
            self._hub.nordpool.prices_tomorrow
        )
        _hvac_offset = self.hvac_offset
        _LOGGER.debug(f"checked offset and ret was {ret}. current offset is {self.current_offset}. Reported hvac offset is {_hvac_offset}")
        if ret != self.current_offset:
            self.current_offset = ret
        if self.current_offset != _hvac_offset:
            return True
        return False

    @abstractmethod
    async def update_system(self, operation: HvacOperations):
        pass










