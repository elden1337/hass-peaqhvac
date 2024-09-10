import time
import logging
import asyncio
from datetime import datetime

from custom_components.peaqhvac.service.models.enums.hvacoperations import HvacOperations

_LOGGER = logging.getLogger(__name__)


async def async_cycle_waterboost(target_temp: float, async_update_system: callable, hub) -> bool:
    end_time = time.time() + 1800
    await async_update_system(operation=HvacOperations.WaterBoost, set_val=1)
    while all([
        time.time() < end_time,
        hub.hvac.water_heater.current_temperature < target_temp
    ]):
        if hub.sensors.peaqev_installed:
            if all([hub.sensors.peaqev_facade.above_stop_threshold, 20 <= datetime.now().minute < 55]):
                _LOGGER.debug("Peak is being breached. Turning off water heating")
                break
        await asyncio.sleep(5)
    await async_update_system(operation=HvacOperations.WaterBoost, set_val=0)
    await asyncio.sleep(180)
    await async_update_system(operation=HvacOperations.WaterBoost, set_val=0)
    hub.observer.broadcast("water boost done")
    hub.hass.bus.fire("peaqhvac.water_heater_warning", {"new": False})
    return True