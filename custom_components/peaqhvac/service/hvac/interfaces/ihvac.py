from __future__ import annotations

import logging
from abc import abstractmethod
import time
from datetime import timedelta
from typing import TYPE_CHECKING, Tuple

from homeassistant.helpers.event import async_track_time_interval
from peaqevcore.common.models.observer_types import ObserverTypes

from custom_components.peaqhvac.service.observer.iobserver_coordinator import IObserver

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


UPDATE_INTERVALS = {
    HvacOperations.Offset:    300,
    HvacOperations.VentBoost: 1800,
}

ADDON_VALUE_CONVERSION = {
            "Alarm":   False,
            "Blocked": False,
            "Off":     False,
            "Active":  True,
        }

HVACMODE_LOOKUP = {
            "Off":       HvacMode.Idle,
            "Hot water": HvacMode.Water,
            "Heating":   HvacMode.Heat,
        }


class IHvac:
    _force_update: bool = False
    update_list: dict[HvacOperations, any] = {}
    periodic_update_timers: dict = {
        HvacOperations.Offset:    0,
        HvacOperations.VentBoost: 0,
    }

    def __init__(self, hass: HomeAssistant, hub: Hub, observer: IObserver):
        self.model = IHvacModel()
        self.hub = hub
        self.observer = observer
        self._hass = hass
        self.house_heater = HouseHeaterCoordinator(hvac=self, hub=hub, observer=observer)
        self.water_heater = WaterHeater(hub=hub, observer=observer)
        self.house_ventilation = HouseVentilation(hvac=self, observer=observer)

        self.observer.add(ObserverTypes.OffsetRecalculation, self.async_update_offset)
        self.observer.add("ObserverTypes.TemperatureIndoorsChanged", self.async_receive_temperature_change)
        async_track_time_interval(self._hass, self.async_receive_temperature_change, timedelta(seconds=60))

    async def async_receive_temperature_change(self, *args):
        await self.async_update_offset()

    @property
    @abstractmethod
    def delta_return_temp(self):
        pass

    @property
    def hvac_mode(self) -> HvacMode:
        """
                    'enumValues': [
                  {
                    'value': '10',
                    'text': 'Off',
                  },
                  {
                    'value': '20',
                    'text': 'Hot water',
                  },
                  {
                    'value': '30',
                    'text': 'Heating',
                  },
                  {
                    'value': '40',
                    'text': 'Pool',
                  },
                  {
                    'value': '41',
                    'text': 'Pool 2',
                  },
                  {
                    'value': '50',
                    'text': 'Transfer',
                  },
                  {
                    'value': '60',
                    'text': 'Cooling',
                  }
                ],
                """

        sensor = self.get_sensor(SensorType.HvacMode)
        ret = self._handle_sensor(sensor)
        if ret is not None:
            return HVACMODE_LOOKUP.get(ret, HvacMode.Unknown)
        return HvacMode.Unknown

    @property
    @abstractmethod
    def fan_speed(self) -> float:
        pass

    @abstractmethod
    def get_sensor(self, sensor: SensorType = None):
        pass

    @abstractmethod
    def set_operation_call_parameters(
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
        if self.model.hvac_dm != ret:
            self.model.hvac_dm = ret
            self.hub.sensors.dm_trend.add_reading(ret, time.time())
        return ret

    @property
    def compressor_frequency(self) -> int:
        return self.get_value(SensorType.CompressorFrequency, int)

    @property
    def hvac_electrical_addon(self) -> bool:
        ret = self.get_value(SensorType.ElectricalAddition, str)
        return ADDON_VALUE_CONVERSION.get(ret, False)

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

    async def async_update_offset(self, raw_offset:int|None = None) -> bool:
        if raw_offset:
            if int(raw_offset) != self.model.raw_offset:
                self.model.raw_offset = int(raw_offset)
        ret = False
        if self.hub.sensors.peaqev_installed:
            if len(self.hub.sensors.peaqev_facade.offsets.get("today", {})) < 20:
                return ret
        try:
            _hvac_offset = self.hvac_offset
            new_offset, force_update = await self.house_heater.async_adjusted_offset(
                self.model.raw_offset
            )
            if new_offset != self.model.current_offset:
                _LOGGER.debug(f"Offset changed from {self.model.current_offset} to {new_offset}, with raw input {self.model.raw_offset}.")
                self.model.current_offset = new_offset
                self._force_update = force_update
            if self.model.current_offset != _hvac_offset:
                await self.observer.async_broadcast(ObserverTypes.OffsetsChanged) #to update waterheater
                await self.observer.async_broadcast(
                    command=ObserverTypes.UpdateOperation,
                    argument=(HvacOperations.Offset, self.model.current_offset)
                )
                ret = True
        except Exception as e:
            _LOGGER.exception(f"Error in updating offsets: {e}")
        finally:
            return ret

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


