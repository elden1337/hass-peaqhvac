from abc import abstractmethod
import logging
from datetime import datetime

from custom_components.peaqhvac.service.hvac.house_heater import HouseHeater
from custom_components.peaqhvac.service.hvac.offset import Offset
from homeassistant.core import (
    HomeAssistant
)

from custom_components.peaqhvac.service.hvac.water_heater import WaterHeater
from custom_components.peaqhvac.service.models.hvacoperations import HvacOperations
from custom_components.peaqhvac.service.models.sensortypes import SensorType

_LOGGER = logging.getLogger(__name__)

class IHvac:
    current_offset: int = 0
    current_offset_dict: dict = {}
    current_offset_dict_tomorrow: dict = {}

    def __init__(self, hass: HomeAssistant, hub):
        self._hub = hub
        self._hass = hass
        self.house_heater = HouseHeater(hvac=self)
        self.water_heater = WaterHeater(hvac=self)

    def get_offset(self) -> bool:
        ret = Offset.getoffset(
            self._hub.options.hvac_tolerance,
            self._hub.nordpool.prices,
            self._hub.nordpool.prices_tomorrow
        )
        self.current_offset_dict = ret[0]
        self.current_offset_dict_tomorrow = ret[1]
        _hvac_offset = self.hvac_offset
        new_offset = self.house_heater.get_current_offset(ret[0])
        if new_offset != self.current_offset:
            self.current_offset = new_offset
        if self.current_offset != _hvac_offset:
            return True
        return False

    def _handle_sensor(self, sensor:str):
        sensorobj = sensor.split('|')
        if len(sensorobj) == 1:
            return self._handle_sensor_basic(sensor)
        elif len(sensorobj) == 2:
            return self._handle_sensor_attribute(sensorobj)
        raise ValueError

    def _handle_sensor_basic(self, sensor:str):
        ret = self._hass.states.get(sensor)
        if ret is not None:
            return ret.state
        return None

    def _handle_sensor_attribute(self, sensorobj):
        ret = self._hass.states.get(sensorobj[0])
        if ret is not None:
            try:
                ret_attr = ret.attributes.get(sensorobj[1])
                return ret_attr
            except Exception as e:
                _LOGGER.exception(e)
        return 0

    @abstractmethod
    def get_sensor(self, sensor: SensorType = None):
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










