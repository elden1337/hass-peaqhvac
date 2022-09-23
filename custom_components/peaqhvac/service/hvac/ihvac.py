from abc import abstractmethod
import logging
from datetime import datetime
from custom_components.peaqhvac.service.hvac.offset import Offset
from homeassistant.core import (
    HomeAssistant
)

from custom_components.peaqhvac.service.models.demand import Demand
from custom_components.peaqhvac.service.models.hvacoperations import HvacOperations
from custom_components.peaqhvac.service.models.sensortypes import SensorType

_LOGGER = logging.getLogger(__name__)

class IHvac:
    current_offset: int = 0
    current_offset_dict: dict = {}
    current_offset_dict_tomorrow: dict = {}
    heating_demand: Demand = Demand.NoDemand
    water_demand: Demand = Demand.NoDemand

    def __init__(self, hass: HomeAssistant, hub):
        self._hub = hub
        self._hass = hass

    def get_offset(self) -> bool:
        ret = Offset.getoffset(
            self._hub.options.hvac_tolerance,
            self._hub.nordpool.prices,
            self._hub.nordpool.prices_tomorrow
        )
        self.current_offset_dict = ret[0]
        self.current_offset_dict_tomorrow = ret[1]
        _hvac_offset = self.hvac_offset
        new_offset = self._get_current_offset(ret[0])
        if new_offset != self.current_offset:
            self.current_offset = new_offset
        if self.current_offset != _hvac_offset:
            return True
        return False

    def _get_current_offset(self, offsets:dict) -> int:
        desired_offset = offsets[datetime.now().hour] - self._get_tempdiff()
        return Offset.adjust_to_threshold(desired_offset, self._hub.options.hvac_tolerance)

    def _get_tempdiff(self) -> int:
        return int((self._hub.sensors.average_temp_indoors.value - self._hub.sensors.set_temp_indoors)/2)

    @abstractmethod
    def get_sensor(self, sensor: SensorType) -> str:
        pass

    @property
    @abstractmethod
    def hvac_offset(self) -> int:
        pass

    @property
    @abstractmethod
    def hvac_dm(self) -> int:
        pass

    @property
    @abstractmethod
    def hvac_watertemp(self) -> float:
        pass

    @abstractmethod
    async def update_system(self, operation: HvacOperations):
        pass










