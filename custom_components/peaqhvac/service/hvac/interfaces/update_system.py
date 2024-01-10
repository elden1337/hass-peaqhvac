from __future__ import annotations
import time
from datetime import datetime
import asyncio
from custom_components.peaqhvac.service.models.enums.hvacoperations import HvacOperations
import logging

_LOGGER = logging.getLogger(__name__)

UPDATE_INTERVALS = {
    HvacOperations.Offset: 300,
    HvacOperations.VentBoost: 1800,
}


async def async_cycle_waterboost(timeout: int, async_update_system: callable, hub) -> bool:
    end_time = time.time() + timeout
    await async_update_system(operation=HvacOperations.WaterBoost, set_val=1)
    while time.time() < end_time:
        if hub.sensors.peaqev_installed:
            if all([hub.sensors.peaqev_facade.above_stop_threshold, 20 <= datetime.now().minute < 55]):
                _LOGGER.debug("Peak is being breached. Turning off water heating")
                break
        await asyncio.sleep(5)
    await async_update_system(operation=HvacOperations.WaterBoost, set_val=0)
    await asyncio.sleep(180)
    await async_update_system(operation=HvacOperations.WaterBoost, set_val=0)
    hub.observer.broadcast("water boost done")
    hub.state_machine.bus.fire("peaqhvac.water_heater_warning", {"new": False})
    return True

class UpdateSystem:
    _force_update: bool = False
    update_list: dict[HvacOperations, any] = {}
    periodic_update_timers: dict = {
        HvacOperations.Offset:     0,
        HvacOperations.VentBoost:  0,
    }

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
        if await self._hass.async_add_executor_job(self.update_offset):
            if await self.async_ready_to_update(HvacOperations.Offset):
                self.update_list[HvacOperations.Offset] = self.current_offset

    async def async_boost_water(self, timer:int) -> None:
        if self.hub.hvac.water_heater.control_module:
            _LOGGER.debug(f"init water boost process")
            self.hub.state_machine.async_create_task(async_cycle_waterboost(timer, self.async_update_system, self.hub))
            _LOGGER.debug(f"return from water boost process")

    async def async_perform_periodic_updates(self) -> None:
        removelist = []
        for operation,v in self.update_list.items():
            if self.timer_timeout(operation):
                if await self.async_update_system(operation=operation, set_val=v):
                    self.periodic_update_timers[operation] = time.time()
                    removelist.append(operation)
        for r in removelist:
            self.update_list.pop(r)

    async def async_update_system(self, operation: HvacOperations, set_val: any = None) -> bool:
        if self.hub.sensors.peaq_enabled.value:
            _value = 0
            if self.hub.sensors.average_temp_outdoors.initialized_percentage > 0.5:
                _value = await self._get_operation_value(operation, set_val)
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
