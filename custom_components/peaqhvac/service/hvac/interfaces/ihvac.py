from __future__ import annotations

import logging
from abc import abstractmethod
from typing import TYPE_CHECKING, Tuple

from custom_components.peaqhvac.service.hvac.house_ventilation import HouseVentilation
from custom_components.peaqhvac.service.hvac.interfaces.update_system import UpdateSystem

if TYPE_CHECKING:
    from custom_components.peaqhvac.service.hub.hub import Hub

from homeassistant.core import HomeAssistant

import custom_components.peaqhvac.extensionmethods as ex
from custom_components.peaqhvac.service.hvac.house_heater import HouseHeater
from custom_components.peaqhvac.service.hvac.water_heater.water_heater_coordinator import WaterHeater
from custom_components.peaqhvac.service.models.enums.hvacmode import HvacMode
from custom_components.peaqhvac.service.models.enums.hvacoperations import HvacOperations
from custom_components.peaqhvac.service.models.enums.sensortypes import SensorType
from custom_components.peaqhvac.service.models.ihvac_model import IHvacModel

_LOGGER = logging.getLogger(__name__)


class IHvac(UpdateSystem):
    current_offset: int = 0  # todo: remove either from here or from house_heater

    def __init__(self, hass: HomeAssistant, hub: Hub):
        self.hub = hub
        self._hass = hass
        self.house_heater = HouseHeater(hvac=self)
        self.water_heater = WaterHeater(hvac=self)
        self.house_ventilation = HouseVentilation(hvac=self)
        self.model = IHvacModel()
        super().__init__(hass, hub, self)
        self.hub.observer.add("offset recalculation", self.update_offset)
        self.hub.observer.add("update operation", self.request_periodic_updates)

    @property
    @abstractmethod
    def delta_return_temp(self):
        pass

    @property
    @abstractmethod
    def hvac_mode(self) -> HvacMode:
        pass

    @property
    @abstractmethod
    def fan_speed(self) -> float:
        pass

    @abstractmethod
    def get_sensor(self, sensor: SensorType = None):
        pass

    @abstractmethod
    def _get_operation_call_parameters(
        self, operation: HvacOperations, _value: any
    ) -> Tuple[str, dict, str]:
        pass

    @abstractmethod
    async def _get_operation_value(
        self, operation: HvacOperations, set_val: any = None
    ):
        pass

    @property
    def hvac_offset(self) -> int:
        return self.get_value(SensorType.Offset, int)

    @property
    def hvac_dm(self) -> int:
        return self.get_value(SensorType.DegreeMinutes, int)

    @property
    def hvac_electrical_addon(self) -> float:
        return self.get_value(SensorType.ElectricalAddition, float)

    @property
    def hvac_compressor_start(self) -> int:
        return self.get_value(SensorType.DMCompressorStart, int)

    @property
    def hvac_watertemp(self) -> float:
        val = self.get_value(SensorType.WaterTemp, float)
        self.water_heater.current_temperature = val
        return val

    async def async_update_hvac(self) -> None:
        await self.house_heater.async_update_demand()
        await self.water_heater.async_update_demand()
        await self.request_periodic_updates()

    def update_offset(self) -> bool:  # todo: make async
        if self.hub.sensors.peaqev_installed:
            if len(self.hub.sensors.peaqev_facade.offsets.get("today", {})) < 20:
                return False
        try:
            self.get_offsets()
            new_offset, force_update = self.house_heater.get_current_offset(
                self.model.current_offset_dict
            )
            if new_offset != self.current_offset:
                self.current_offset = new_offset
                self._force_update = force_update
            if self.current_offset != self.hvac_offset:
                return True
            return False
        except Exception as e:
            _LOGGER.exception(f"Error on updating offsets: {e}")
            return False

    def get_offsets(self) -> None:  # todo: make async
        ret = self.hub.offset.get_offset()
        if ret is not None:
            self.model.current_offset_dict = ret[0]
            self.model.current_offset_dict_tomorrow = ret[1]

    @staticmethod
    def _get_sensors_for_callback(types: dict) -> list:
        ret = []
        for t in types:
            item = types[t]
            ret.append(item.split("|")[0])
        return ret

    def get_value(self, sensor: SensorType, return_type):
        _sensor = self.get_sensor(sensor)
        ret = self._handle_sensor(_sensor)
        if ret is not None:
            try:
                return ex.parse_to_type(ret, return_type)
            except Exception as e:
                _LOGGER.debug(f"Could not parse {sensor.name} from hvac. {e}")
        return 0

    def _handle_sensor(self, sensor: str):
        sensor_obj = sensor.split("|")
        if 0 < len(sensor_obj) <= 2:
            ret = self._hass.states.get(sensor_obj[0])
            if ret is not None:
                if len(sensor_obj) == 2:
                    try:
                        ret_attr = ret.attributes.get(sensor_obj[1])
                        return ret_attr
                    except Exception as e:
                        _LOGGER.exception(e)
                else:
                    return ret.state
            return None
        raise ValueError

