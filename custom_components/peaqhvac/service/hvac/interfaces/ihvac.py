from __future__ import annotations

import asyncio
import logging
from abc import abstractmethod
import time
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Tuple

from peaqevcore.common.models.observer_types import ObserverTypes

from custom_components.peaqhvac.service.hvac.water_heater.cycle_waterboost import async_cycle_waterboost
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
        self._hvac_dm: int = None
        self.raw_offset: int = 0
        self.house_heater = HouseHeaterCoordinator(hvac=self, hub=hub)
        self.water_heater = WaterHeater(hub=hub, observer=observer)
        self.house_ventilation = HouseVentilation(hvac=self, observer=observer)

        self.observer.add(ObserverTypes.OffsetRecalculation, self.async_update_offset)
        self.observer.add("water boost start", self.async_boost_water)

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

    async def async_update_offset(self, raw_offset:int|None = None) -> bool:
        if raw_offset:
            if int(raw_offset) != self.raw_offset:
                _LOGGER.debug(f"Raw offset pushed to update offset: {raw_offset}. Previous {self.raw_offset}")
                self.raw_offset = int(raw_offset)
        ret = False
        if self.hub.sensors.peaqev_installed:
            if len(self.hub.sensors.peaqev_facade.offsets.get("today", {})) < 20:
                return ret
        try:
            _hvac_offset = self.hvac_offset
            new_offset, force_update = await self.house_heater.async_adjusted_offset(
                self.raw_offset
            )
            if new_offset != self.model.current_offset:
                self.model.current_offset = new_offset
                self._force_update = force_update
            if self.model.current_offset != _hvac_offset:
                await self.observer.async_broadcast(ObserverTypes.OffsetsChanged)
                #if self._force_update:
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

    async def request_periodic_updates(self) -> None:
        await self.async_update_ventilation()
        if self.hub.hvac.house_heater.control_module:
            await self.async_update_heat()
        await self.async_perform_periodic_updates()

    async def async_update_ventilation(self) -> None:
        if self.house_ventilation.booster_update:
            if await self.async_ready_to_update(HvacOperations.VentBoost):
                _vent_state = int(self.house_ventilation.vent_boost)
                if _vent_state != self.update_list.get(HvacOperations.VentBoost, None):
                    _LOGGER.debug(f"Vent boost state changed to {_vent_state}. Adding to update list.")
                    self.update_list[HvacOperations.VentBoost] = _vent_state

    async def async_update_heat(self) -> None:
        if await self.async_update_offset():
            if await self.async_ready_to_update(HvacOperations.Offset):
                self.update_list[HvacOperations.Offset] = self.model.current_offset

    async def async_boost_water(self, target_temp: float) -> None:
        if self.hub.hvac.water_heater.control_module:
            _LOGGER.debug(f"init water boost process")
            self.hub.state_machine.async_create_task(
                async_cycle_waterboost(target_temp, self.async_update_system, self.hub))
            _LOGGER.debug(f"return from water boost process")

    async def async_perform_periodic_updates(self) -> None:
        removelist = []
        for operation, v in self.update_list.items():
            if self.timer_timeout(operation):
                if await self.async_update_system(operation=operation, set_val=v):
                    self.periodic_update_timers[operation] = time.time()
                    removelist.append(operation)
        for r in removelist:
            self.update_list.pop(r)

    async def async_update_system(self, operation: HvacOperations, set_val: any = None) -> bool:
        if self.hub.sensors.peaqhvac_enabled.value:
            _value = set_val
            if self.hub.sensors.average_temp_outdoors.initialized_percentage > 0.5:
                (
                    call_operation,
                    params,
                    domain,
                ) = self.set_operation_call_parameters(operation, _value)

                await self._hass.services.async_call(domain, call_operation, params)
                _LOGGER.debug(
                    f"Requested to update hvac-{operation.name} with value {set_val}. Actual value: {params} for {call_operation}"
                )
                return True
        return False

    def timer_timeout(self, operation) -> bool:
        return time.time() - self.periodic_update_timers[operation] > UPDATE_INTERVALS[operation]

    async def async_ready_to_update(self, operation) -> bool:
        match operation:
            case HvacOperations.WaterBoost | HvacOperations.VentBoost:
                return any(
                    [
                        self.timer_timeout(operation),
                        self.hub.sensors.peaqev_facade.exact_threshold >= 100,
                    ]
                )
            case HvacOperations.Offset:
                if not self.hub.hvac.house_heater.control_module:
                    return False
                if self._force_update:
                    self._force_update = False
                    return True
                return any(
                    [
                        self.timer_timeout(operation),
                        datetime.now().minute == 0,
                        self.hub.sensors.peaqev_facade.exact_threshold >= 100,
                    ]
                )
            case _:
                return False
