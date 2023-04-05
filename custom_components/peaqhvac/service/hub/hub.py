import logging

from custom_components.peaqhvac.service.hub.hubsensors import HubSensors
from custom_components.peaqhvac.service.hub.nordpool import NordPoolUpdater
from custom_components.peaqhvac.service.hub.state_changes import StateChanges
from custom_components.peaqhvac.service.hub.weather_prognosis import WeatherPrognosis
from custom_components.peaqhvac.service.hvac.hvacfactory import HvacFactory
from custom_components.peaqhvac.service.hvac.offset.offset_coordinator import OffsetCoordinator
from custom_components.peaqhvac.service.models.config_model import ConfigModel
from homeassistant.helpers.event import async_track_state_change
from homeassistant.core import (
    HomeAssistant,
    callback
)

from custom_components.peaqhvac.service.observer import Observer

_LOGGER = logging.getLogger(__name__)


class Hub:
    hub_id = 1338
    hubname = "PeaqHvac"

    def __init__(self, hass: HomeAssistant, hub_options: ConfigModel):
        self._is_initialized = False
        self._hass = hass
        self.observer = Observer(self)
        self.options = hub_options
        self.sensors = HubSensors(self, hub_options, self._hass, self.get_peaqev())
        self.states = StateChanges(self, self._hass)
        self.hvac = HvacFactory.create(self._hass, self.options, self)
        self.nordpool = NordPoolUpdater(self._hass, self)
        self.prognosis = WeatherPrognosis(self)
        self.offset = OffsetCoordinator(self)
        self.options.hub = self

    async def async_setup(self) -> None:
        await self.nordpool.async_setup()
        await self.async_setup_trackers()

    async def async_setup_trackers(self):
        self.trackerentities = []
        self.trackerentities.append(self.nordpool.nordpool_entity)
        self.trackerentities.extend(self.options.indoor_tempsensors)
        self.trackerentities.extend(self.options.outdoor_tempsensors)
        await self.states.async_initialize_values()
        async_track_state_change(self._hass, self.trackerentities, self.async_state_changed)

    @property
    def is_initialized(self) -> bool:
        if self._is_initialized:
            return True
        return self._check_initialized()

    def _check_initialized(self) -> bool:
        if all([
            self.nordpool.is_initialized, 
            self.prognosis.is_initialized
        ]):
            self._is_initialized = True
            self.observer.activate()
            return True
        return False

    @callback
    async def async_state_changed(self, entity_id, old_state, new_state):
        if entity_id is not None:
            try:
                if old_state is None or old_state != new_state:
                    await self.states.async_update_sensor(entity_id, new_state.state)
            except Exception as e:
                _LOGGER.exception(f"Unable to handle data: {entity_id} old: {old_state}, new: {new_state}. Raised expection: {e}")

    def get_peaqev(self):
        try:
            ret = self._hass.states.get("sensor.peaqev_threshold")
            if ret is not None:
                _LOGGER.debug("Discovered Peaqev-entities, will adhere to peak-shaving.")
                return True
            _LOGGER.debug("Unable to discover Peaqev-entities, will not adhere to peak-shaving.")
            return False
        except:
            _LOGGER.debug("Unable to discover Peaqev-entities, will not adhere to peak-shaving.")
            return False

    async def call_enable_peaq(self):
        self.sensors.peaq_enabled.value = True

    async def call_disable_peaq(self):
        self.sensors.peaq_enabled.value = False

    async def call_set_mode(self, mode):
        #match towards enum. set hub to that state.
        pass

    @property
    def predicted_temp(self) -> float:
        return self.sensors.average_temp_indoors.value + self.sensors.temp_trend_indoors.gradient
    