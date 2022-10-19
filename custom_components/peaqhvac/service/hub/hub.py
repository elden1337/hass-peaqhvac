import logging

from custom_components.peaqhvac.service.hub.hubsensors import HubSensors
from custom_components.peaqhvac.service.hub.nordpool import NordPoolUpdater
from custom_components.peaqhvac.service.hub.state_changes import StateChanges
from custom_components.peaqhvac.service.hvac.hvacfactory import HvacFactory
from custom_components.peaqhvac.service.models.config_model import ConfigModel
from homeassistant.helpers.event import async_track_state_change
from homeassistant.core import (
    HomeAssistant,
    callback
)

_LOGGER = logging.getLogger(__name__)


class Hub:
    hub_id = 1338
    hubname = "PeaqHvac"

    def __init__(self, hass: HomeAssistant, hub_options: ConfigModel):
        self._hass = hass
        self.options = hub_options
        self.sensors = HubSensors(hub_options, self._hass, self.get_peaqev())
        self.states = StateChanges(self, self._hass)
        self.hvac = HvacFactory.create(self._hass, self.options, self)
        self.nordpool = NordPoolUpdater(self._hass, self)
        self.trackerentities = []
        self.trackerentities.append(self.nordpool.nordpool_entity)
        self.trackerentities.extend(self.options.indoor_tempsensors)
        self.trackerentities.extend(self.options.outdoor_tempsensors)
        self.states.initialize_values()

        async_track_state_change(hass, self.trackerentities, self.state_changed)

    @callback
    async def state_changed(self, entity_id, old_state, new_state):
        if entity_id is not None:
            try:
                if old_state is None or old_state != new_state:
                    await self.states.update_sensor_async(entity_id, new_state.state)
            except Exception as e:
                _LOGGER.exception(f"Unable to handle data: {entity_id} old: {old_state}, new: {new_state}. Raised expection: {e}")

    def get_peaqev(self):
        ret = self._hass.states.get("sensor.peaqev_threshold")
        if ret is not None:
            _LOGGER.debug("Discovered Peaqev-entities, will adhere to peak-shaving.")
            return True
        _LOGGER.debug("Unable to discover Peaqev-entities, will not adhere to peak-shaving.")
        return False

    async def call_enable_peaq(self):
        self.sensors.peaq_enabled.value = True

    async def call_disable_peaq(self):
        self.sensors.peaq_enabled.value = False

    async def call_set_mode(self, mode):
        #match towards enum. set hub to that state.
        pass