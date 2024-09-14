from __future__ import annotations

import logging
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
from custom_components.peaqhvac.service.models.enums.hvacoperations import HvacOperations
from custom_components.peaqhvac.service.models.enums.sensortypes import SensorType
from custom_components.peaqhvac.service.models.ihvac_model import IHvacModel

_LOGGER = logging.getLogger(__name__)


UPDATE_INTERVALS = {
    HvacOperations.Offset:    180,
    HvacOperations.VentBoost: 1800,
}


class UpdateSystem:
    _force_update: bool = False
    update_list: dict[HvacOperations, any] = {}
    periodic_update_timers: dict = {
        HvacOperations.Offset:    0,
        HvacOperations.VentBoost: 0,
    }

    def __init__(self, hass: HomeAssistant, hub: Hub, observer: IObserver):
        self.hub = hub
        self.observer = observer
        self._hass = hass
        self._hvac_dm: int = None
        self.raw_offset: int = 0


        #self.observer.add(ObserverTypes.OffsetRecalculation, self.async_update_offset)
        self.observer.add(ObserverTypes.UpdateOperation, self.request_periodic_updates)
        self.observer.add("water boost start", self.async_boost_water)

    # @staticmethod
    # def _get_sensors_for_callback(types: dict) -> list:
    #     ret = []
    #     for t in types:
    #         item = types[t]
    #         ret.append(item.split("|")[0])
    #     return ret
    #
    # def get_value(self, sensor: SensorType, return_type):
    #     _sensor = self.get_sensor(sensor)
    #     ret = self._handle_sensor(_sensor)
    #     if ret is not None:
    #         try:
    #             return ex.parse_to_type(ret, return_type)
    #         except Exception as e:
    #             _LOGGER.debug(f"Could not parse {sensor.name} from hvac. {e}")
    #     return 0
    #
    # def _handle_sensor(self, sensor: str):
    #     sensor_obj = sensor.split("|")
    #     if not 0 < len(sensor_obj) <= 2:
    #         raise ValueError
    #     entity_id = sensor_obj[0]
    #     state = self._hass.states.get(entity_id)
    #     if state is None:
    #         return None
    #     if len(sensor_obj) == 2:
    #         attribute = sensor_obj[1]
    #         try:
    #             return state.attributes.get(attribute)
    #         except Exception as e:
    #             _LOGGER.exception(e)
    #             return None
    #     return state.state

    async def async_receive_request(self, request: Tuple[HvacOperations, any]) -> None:
        #add the request to the update_list if we are controling the module in question. If not, we will ignore the request.
        operation, value = request

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
        if await self.async_update_offset(): #todo: cannot do that from here anymore
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
                ) = self._set_operation_call_parameters(operation, _value)

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
