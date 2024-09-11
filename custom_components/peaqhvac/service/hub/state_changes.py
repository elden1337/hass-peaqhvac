from __future__ import annotations
import logging
import time

from peaqevcore.common.wait_timer import WaitTimer
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from custom_components.peaqhvac.service.hub.hub import Hub

_LOGGER = logging.getLogger(__name__)


class StateChanges:
    def __init__(self, hub, hass):
        self._hub: Hub = hub
        self._hass = hass
        self.latest_nordpool_update = WaitTimer(timeout=300)

    async def async_initialize_values(self):
        for t in self._hub.trackerentities:
            retval = self._hass.states.get(t)
            if retval is not None:
                await self.async_update_sensor(entity=t, value=retval.state)

    async def _update_indoor_sensor(self, entity, value):
        await self._hub.sensors.average_temp_indoors.async_update_values(entity=entity, value=value)
        await self._hub.sensors.temp_trend_indoors.async_add_reading(val=self._hub.sensors.average_temp_indoors.value,
                                                                     t=time.time())

    async def _update_outdoor_sensor(self, entity, value):
        await self._hub.sensors.average_temp_outdoors.async_update_values(entity=entity, value=value)
        await self._hub.sensors.temp_trend_outdoors.async_add_reading(val=self._hub.sensors.average_temp_outdoors.value,
                                                                      t=time.time())

    async def async_update_sensor(self, entity, value):
        if entity in self._hub.options.indoor_tempsensors:
            await self._update_indoor_sensor(entity, value)
        elif entity in self._hub.options.outdoor_tempsensors:
            await self._update_outdoor_sensor(entity, value)

        await self._hass.async_add_executor_job(self._hub.prognosis.get_hvac_prognosis,
                                                self._hub.sensors.average_temp_outdoors.value)

        if entity == self._hub.spotprice.entity or self.latest_nordpool_update.is_timeout():
            await self._hub.spotprice.async_update_spotprice()
            await self._hass.async_add_executor_job(self._hub.prognosis.update_weather_prognosis)
            self.latest_nordpool_update.update()

        await self._hub.hvac_service.async_update_hvac()
