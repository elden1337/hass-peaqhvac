from __future__ import annotations

import logging
import time
from abc import abstractmethod
from datetime import datetime
from typing import TYPE_CHECKING, Tuple

if TYPE_CHECKING:
    from custom_components.peaqhvac.service.hub.hub import Hub

from homeassistant.core import HomeAssistant

import custom_components.peaqhvac.extensionmethods as ex
from custom_components.peaqhvac.service.hvac.house_heater import HouseHeater
from custom_components.peaqhvac.service.hvac.water_heater.water_heater_coordinator import \
    WaterHeater
from custom_components.peaqhvac.service.models.enums.hvacmode import HvacMode
from custom_components.peaqhvac.service.models.enums.hvacoperations import \
    HvacOperations
from custom_components.peaqhvac.service.models.enums.sensortypes import \
    SensorType
from custom_components.peaqhvac.service.models.ihvac_model import IHvacModel

_LOGGER = logging.getLogger(__name__)

UPDATE_INTERVALS = {
    HvacOperations.Offset: 900,
    HvacOperations.WaterBoost: 60,
    HvacOperations.VentBoost: 1800,
}


class IHvac:
    current_offset: int = 0  # todo: remove either from here or from house_heater

    def __init__(self, hass: HomeAssistant, hub: Hub):
        self.hub = hub
        self._hass = hass
        self._force_update: bool = False
        self.house_heater = HouseHeater(hvac=self)
        self.water_heater = WaterHeater(hvac=self)
        self.periodic_update_timers: dict = {
            HvacOperations.Offset: 0,
            HvacOperations.WaterBoost: 0,
            HvacOperations.VentBoost: 0,
        }
        self.model = IHvacModel()
        self.hub.observer.add("offset recalculation", self.update_offset)

    def update_offset(self) -> bool:  # todo: make async
        if self.hub.sensors.peaqev_installed:
            if len(self.hub.sensors.peaqev_facade.offsets.get("today", {})) < 20:
                return False
        try:
            self.get_offsets()
            _hvac_offset = self.hvac_offset
            new_offset, force_update = self.house_heater.get_current_offset(
                self.model.current_offset_dict
            )
            if new_offset != self.current_offset:
                self.current_offset = new_offset
                self._force_update = force_update
            if self.current_offset != _hvac_offset:
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

    @property
    @abstractmethod
    def delta_return_temp(self):
        pass

    @property
    @abstractmethod
    def hvac_mode(self) -> HvacMode:
        pass

    @abstractmethod
    def get_sensor(self, sensor: SensorType = None):
        pass

    @abstractmethod
    async def _get_operation_call_parameters(
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

    async def async_ready_to_update(self, operation) -> bool:
        match operation:
            case HvacOperations.WaterBoost | HvacOperations.VentBoost:
                return any(
                    [
                        time.time() - self.periodic_update_timers[operation]
                        > UPDATE_INTERVALS[operation],
                        self.hub.sensors.peaqev_facade.exact_threshold >= 100,
                    ]
                )
            case HvacOperations.Offset:
                if self._force_update:
                    self._force_update = False
                    return True
                return any(
                    [
                        time.time() - self.periodic_update_timers[operation]
                        > UPDATE_INTERVALS[operation],
                        datetime.now().minute == 0,
                    ]
                )
            case _:
                return False

    async def request_periodic_updates(self) -> None:
        if self.hub.hvac.water_heater.control_module:
            await self.async_request_periodic_updates_water()
        if self.hub.hvac.house_heater.control_module:
            await self.async_request_periodic_updates_heat()
        return await self._do_periodic_updates()

    async def async_request_periodic_updates_heat(self) -> None:
        _vent_state = int(self.house_heater.vent_boost)
        if _vent_state != self.model.current_vent_boost_state:
            if await self.async_ready_to_update(HvacOperations.VentBoost):
                self.model.update_list.append((HvacOperations.VentBoost, _vent_state))
                self.model.current_vent_boost_state = _vent_state
        if await self._hass.async_add_executor_job(self.update_offset):
            if await self.async_ready_to_update(HvacOperations.Offset):
                self.model.update_list.append(
                    (HvacOperations.Offset, self.current_offset)
                )

    async def async_request_periodic_updates_water(self) -> None:
        if self.water_heater.try_heat_water or self.water_heater.water_heating:
            if await self.async_ready_to_update(HvacOperations.WaterBoost):
                if self.model.current_water_boost_state != int(
                    self.water_heater.try_heat_water
                ):
                    self.model.update_list.append(
                        (
                            HvacOperations.WaterBoost,
                            int(self.water_heater.try_heat_water),
                        )
                    )
                    self.model.current_water_boost_state = int(
                        self.water_heater.try_heat_water
                    )

    async def _do_periodic_updates(self) -> None:
        if len(self.model.update_list) > 0:
            for u in self.model.update_list:
                await self.update_system(operation=u[0], set_val=u[1])
                self.periodic_update_timers[u[0]] = time.time()
            self.model.update_list = []

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

    def _get_sensors_for_callback(self, types: dict) -> list:
        ret = []
        for t in types:
            item = types[t]
            ret.append(item.split("|")[0])
        self.model.listenerentities = ret
        return ret

    async def update_system(self, operation: HvacOperations, set_val: any = None):
        if self.hub.sensors.peaq_enabled.value:
            _value = 0
            if self.hub.sensors.average_temp_outdoors.initialized_percentage > 0.5:
                _value = await self._get_operation_value(operation, set_val)
                (
                    call_operation,
                    params,
                    domain,
                ) = await self._get_operation_call_parameters(operation, _value)

                _LOGGER.debug(
                    f"Requesting to update hvac-{operation.name} with value {set_val}"
                )
                await self._hass.services.async_call(domain, call_operation, params)

    def get_value(self, sensor: SensorType, return_type):
        _sensor = self.get_sensor(sensor)
        ret = self._handle_sensor(_sensor)
        if ret is not None:
            try:
                return ex.parse_to_type(ret, return_type)
            except Exception as e:
                _LOGGER.debug(f"Could not parse {sensor.name} from hvac. {e}")
        return 0
