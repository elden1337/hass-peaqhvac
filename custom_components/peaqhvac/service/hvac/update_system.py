from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Tuple

from homeassistant.helpers.event import async_track_time_interval
from peaqevcore.common.models.observer_types import ObserverTypes

from custom_components.peaqhvac.service.hvac.water_heater.cycle_waterboost import async_cycle_waterboost
from custom_components.peaqhvac.service.observer.iobserver_coordinator import IObserver

if TYPE_CHECKING:
    from custom_components.peaqhvac.service.hub.hub import Hub

from homeassistant.core import HomeAssistant
from custom_components.peaqhvac.service.models.enums.hvacoperations import HvacOperations

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

    def __init__(self, hass: HomeAssistant, hub: Hub, observer: IObserver, operation_params_func: callable):
        self.hub = hub
        self._set_operation_call_parameters: callable = operation_params_func
        self.observer = observer
        self._hass = hass
        async_track_time_interval(
            self._hass, self.async_perform_periodic_updates, timedelta(minutes=5)
        )
        self.observer.add(ObserverTypes.UpdateOperation, self.async_receive_request)
        self.observer.add("water boost start", self.async_boost_water)

    async def async_receive_request(self, request: Tuple[HvacOperations, any]) -> None:
        operation, value = request
        if operation == HvacOperations.Offset and self.hub.hvac.house_heater.control_module:
            self.update_list[operation] = value
        if operation == HvacOperations.VentBoost:
            if value != self.update_list.get(HvacOperations.VentBoost, None):
                self.update_list[operation] = value
        await self.async_perform_periodic_updates()

    async def async_boost_water(self, target_temp: float) -> None:
        if self.hub.hvac.water_heater.control_module:
            _LOGGER.debug(f"init water boost process")
            self._hass.async_create_task(
                async_cycle_waterboost(target_temp, self.async_update_system, self.hub))
            _LOGGER.debug(f"return from water boost process")

    async def async_perform_periodic_updates(self, *args) -> None:
        remove_list = []
        for operation, v in self.update_list.items():
            if self.timer_timeout(operation):
                if await self.async_update_system(operation=operation, set_val=v):
                    self.periodic_update_timers[operation] = time.time()
                    remove_list.append(operation)
        for r in remove_list:
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
