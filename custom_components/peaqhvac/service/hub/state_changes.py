import logging
import time

from custom_components.peaqhvac.service.models.hvacoperations import HvacOperations

_LOGGER = logging.getLogger(__name__)

class StateChanges:
    latest_nordpool_update = 0

    def __init__(self, hub, hass):
        self._hub = hub
        self._hass = hass

    def initialize_values(self):
        for t in self._hub.trackerentities:
            retval = self._hass.states.get(t)
            if retval is not None:
                _LOGGER.debug(f"Initializing {t} with {retval.state}")
                self.update_sensor(entity=t, value=retval.state)

    def update_sensor(self, entity, value):
        if entity in self._hub.options.indoor_tempsensors:
            self._hub.sensors.average_temp_indoors.update_values(entity=entity, value=value)
        elif entity in self._hub.options.outdoor_tempsensors:
            self._hub.sensors.average_temp_outdoors.update_values(entity=entity, value=value)
        elif entity == self._hub.nordpool.nordpool_entity:
            self._hub.nordpool.update_nordpool()
            self._hub.hvac.get_offset()

        """always update the trend-sensors to get gradient"""
        self._hub.sensors.temp_trend_indoors.value = value
        self._hub.sensors.temp_trend_outdoors.value = value

    async def update_sensor_async(self, entity, value):
        if entity in self._hub.options.indoor_tempsensors:
            self._hub.sensors.average_temp_indoors.update_values(entity=entity, value=value)
        elif entity in self._hub.options.outdoor_tempsensors:
            self._hub.sensors.average_temp_outdoors.update_values(entity=entity, value=value)

        if entity == self._hub.nordpool.nordpool_entity or time.time() - self.latest_nordpool_update > 300:
            self._hub.nordpool.update_nordpool()
            self.latest_nordpool_update = time.time()
            if self._hub.hvac.get_offset():
                await self._hub.hvac.update_system(HvacOperations.Offset)

        """always update the trend-sensors to get gradient"""
        self._hub.sensors.temp_trend_indoors.value = value
        self._hub.sensors.temp_trend_outdoors.value = value
