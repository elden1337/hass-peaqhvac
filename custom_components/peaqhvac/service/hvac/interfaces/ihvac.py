from __future__ import annotations

import logging
from abc import abstractmethod
import time
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Tuple

from peaqevcore.common.models.observer_types import ObserverTypes
from custom_components.peaqhvac.service.hvac.interfaces.update_system import UpdateSystem

if TYPE_CHECKING:
    from custom_components.peaqhvac.service.hub.hub import Hub

from homeassistant.core import HomeAssistant

import custom_components.peaqhvac.extensionmethods as ex
from custom_components.peaqhvac.service.hvac.house_heater.house_heater_coordinator import HouseHeaterCoordinator
from custom_components.peaqhvac.service.hvac.water_heater.water_heater_coordinator import WaterHeater
from custom_components.peaqhvac.service.hvac.house_ventilation import HouseVentilation
from custom_components.peaqhvac.service.models.enums.hvacmode import HvacMode
from custom_components.peaqhvac.service.models.enums.hvacoperations import HvacOperations
from custom_components.peaqhvac.service.models.enums.sensortypes import SensorType
from custom_components.peaqhvac.service.models.ihvac_model import IHvacModel

_LOGGER = logging.getLogger(__name__)


class IHvac(UpdateSystem):

    def __init__(self, hass: HomeAssistant, hub: Hub):
        self.model = IHvacModel()
        self.hub = hub
        self._hass = hass
        self._hvac_dm: int = None
        self.house_heater = HouseHeaterCoordinator(hvac=self, hub=hub)
        self.water_heater = WaterHeater(hub=hub)
        self.house_ventilation = HouseVentilation(hvac=self)

        self.hub.observer.add(ObserverTypes.OffsetRecalculation, self.update_offset)
        self.hub.observer.add(ObserverTypes.UpdateOperation, self.request_periodic_updates)
        self.hub.observer.add("water boost start", self.async_boost_water)

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
    def _set_operation_call_parameters(
            self, operation: HvacOperations, _value: any
    ) -> Tuple[str, dict, str]:
        pass

    @property
    def hvac_offset(self) -> int:
        return self.get_value(SensorType.Offset, int)

    @property
    def hvac_dm(self) -> int:
        ret = self.get_value(SensorType.DegreeMinutes, int)
        if ret not in range(-10000, 101):
            _LOGGER.warning(f"DM is out of range: {ret}")
        if self._hvac_dm != ret:
            self._hvac_dm = ret
            self.hub.sensors.dm_trend.add_reading(ret, time.time())
        return ret

    @property
    def compressor_frequency(self) -> int:
        return self.get_value(SensorType.CompressorFrequency, int)

    @property
    def hvac_electrical_addon(self) -> bool:
        value_conversion = {
            "Alarm":   False,
            "Blocked": False,
            "Off":     False,
            "Active":  True,
        }
        ret = self.get_value(SensorType.ElectricalAddition, str)
        return value_conversion.get(ret, False)

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
        await self.house_ventilation.async_check_vent_boost()
        await self.request_periodic_updates()

    def update_offset(self) -> bool:  # todo: make async
        if self.hub.sensors.peaqev_installed:
            if len(self.hub.sensors.peaqev_facade.offsets.get("today", {})) < 20:
                return False
        try:
            self.get_offsets()
            _hvac_offset = self.hvac_offset
            new_offset, force_update = self.house_heater.get_current_offset()
            if new_offset != self.model.current_offset:
                self.model.current_offset = new_offset
                self._force_update = force_update
            if self.model.current_offset != _hvac_offset:
                self.hub.observer.broadcast(ObserverTypes.OffsetsChanged)
                return True
            return False
        except Exception as e:
            _LOGGER.exception(f"Error on updating offsets: {e}")
            return False

    def get_offsets(self) -> None:  # todo: make async
        ret = self.hub.offset.get_offset()
        if ret is not None:
            self.model.current_offset_dict = {k: v for k, v in ret.calculated_offsets.items() if
                                              k.date() == datetime.now().date()}
            self.model.current_offset_dict_tomorrow = {k: v for k, v in ret.calculated_offsets.items() if
                                                       k.date() == datetime.now().date() + timedelta(days=1)}
            self.model.current_offset_dict_combined = ret.calculated_offsets
        else:
            _LOGGER.debug("get_offsets returned None where it should not")

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
        if not 0 < len(sensor_obj) <= 2:
            raise ValueError
        entity_id = sensor_obj[0]
        state = self._hass.states.get(entity_id)
        if state is None:
            return None
        if len(sensor_obj) == 2:
            attribute = sensor_obj[1]
            try:
                return state.attributes.get(attribute)
            except Exception as e:
                _LOGGER.exception(e)
                return None
        return state.state
