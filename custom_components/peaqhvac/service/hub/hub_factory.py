import logging
from homeassistant.core import HomeAssistant
from homeassistant.helpers.event import async_track_state_change_event

from custom_components.peaqhvac import Hub
from custom_components.peaqhvac.service.hvac.hvacfactory import HvacFactory
from custom_components.peaqhvac.service.models.config_model import ConfigModel
from custom_components.peaqhvac.service.observer.observer_coordinator import Observer
from custom_components.peaqhvac.service.hub.hubsensors import HubSensors
from custom_components.peaqhvac.service.hub.state_changes import StateChanges
from custom_components.peaqhvac.service.hub.weather_prognosis import WeatherPrognosis
from custom_components.peaqhvac.service.hvac.offset.offset_coordinator_factory import (
    OffsetFactory,
)
import sys

if "pytest" not in sys.modules:
    from peaqevcore.common.spotprice.spotprice_factory import SpotPriceFactory
    from peaqevcore.common.models.peaq_system import PeaqSystem

_LOGGER = logging.getLogger(__name__)


class HubFactory:
    def __init__(self, hass: HomeAssistant):
        self.hass = hass
        self.hub = None

    async def async_create(self, options: ConfigModel) -> Hub:
        _LOGGER.debug("Entering async_create in hub_factory")
        observer = Observer(self.hass)
        _LOGGER.debug("Hubfactory > Created observer")
        options.observer = observer
        options.misc_options.peaqev_discovered = self._get_peaqev()
        _LOGGER.debug("Hubfactory > Created options and set peaqev_discovered")

        hub = Hub(self.hass, observer, options)
        _LOGGER.debug("Hubfactory > Created hub")
        spotprice = SpotPriceFactory.create(
            hub=hub,
            observer=observer,
            system=PeaqSystem.PeaqHvac,
            test=False,
            is_active=True,
        )
        _LOGGER.debug("Hubfactory > Created spotprice")
        sensors = HubSensors(observer=observer, options=options, hass=self.hass)
        _LOGGER.debug("Hubfactory > Created sensors")
        states = StateChanges(hub, self.hass)
        _LOGGER.debug("Hubfactory > Created states")
        self.hub = hub
        await self.async_setup(spotprice, sensors, states)
        return hub

    async def async_setup(self, spotprice, sensors, states) -> None:
        self.hub.sensors = sensors
        self.hub.states = states
        self.hub.spotprice = spotprice

        self.hub.hvac_service = HvacFactory.create(
            self.hass, self.hub.options, self.hub, self.hub.observer
        )
        _LOGGER.debug("Hubfactory > Created hvacfactory")
        self.hub.prognosis = WeatherPrognosis(
            self.hass, sensors.average_temp_outdoors, self.hub.observer
        )
        _LOGGER.debug("Hubfactory > Created prognosis")
        self.hub.offset = OffsetFactory.create(self.hub, self.hub.observer)
        _LOGGER.debug("Hubfactory > Created offset")
        await self.async_setup_trackers()

    async def async_setup_trackers(self):
        self.hub.trackerentities.append(self.hub.spotprice.entity)
        self.hub.trackerentities.extend(self.hub.options.indoor_tempsensors)
        self.hub.trackerentities.extend(self.hub.options.outdoor_tempsensors)
        await self.hub.states.async_initialize_values()
        async_track_state_change_event(
            self.hass, self.hub.trackerentities, self.hub.async_on_change
        )

    def _get_peaqev(self):
        try:
            ret = self.hass.states.get("sensor.peaqev_threshold")
            if ret is not None:
                if ret.state:
                    _LOGGER.debug(
                        "Discovered Peaqev-entities, will adhere to peak-shaving."
                    )
                    return True
            _LOGGER.debug(
                "Unable to discover Peaqev-entities, will not adhere to peak-shaving."
            )
            return False
        except Exception as e:
            _LOGGER.debug(
                f"Unable to discover Peaqev-entities, will not adhere to peak-shaving. Exception {e}"
            )
            return False
