import logging

_LOGGER = logging.getLogger(__name__)

class StateChanges:
    latest_nordpool_update = 0

    def __init__(self, hub, hass):
        self._hub = hub
        self._hass = hass

    async def initialize_values(self):
        for t in self._hub.trackerentities:
            retval = self._hass.states.get(t)
            await self.update_sensor(entity=t, value=retval)

    async def update_sensor(self, entity, value):
        if entity in self._hub.options.indoor_tempsensors:
            _LOGGER.debug(f"updating indoors with: {entity}, {value}")
            self._hub.sensors.average_temp_indoors.update_values(entity=entity, value=value)
        elif entity in self._hub.options.outdoor_tempsensors:
            _LOGGER.debug(f"updating outdoors with: {entity}, {value}")
            self._hub.sensors.average_temp_outdoors.update_values(entity=entity, value=value)

        """always update the trend-sensors to get gradient"""
        self._hub.sensors.temp_trend_indoors.value = value
        self._hub.sensors.temp_trend_outdoors.value = value
