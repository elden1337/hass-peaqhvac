import logging
from homeassistant.core import HomeAssistant

from custom_components.peaqhvac import Hub
from custom_components.peaqhvac.service.models.config_model import ConfigModel
from custom_components.peaqhvac.service.observer.observer_coordinator import Observer

_LOGGER = logging.getLogger(__name__)


async def async_create(hass: HomeAssistant, options: ConfigModel) -> Hub:
    observer = Observer(hass)
    options.observer = observer
    options.misc_options.peaqev_discovered = _get_peaqev(hass)

    hub = Hub(hass, observer, options)
    return hub

    # self.sensors = HubSensors(self, hub_options, hass, self.peaqev_discovered)
    # self.states = StateChanges(self, hass)
    # self.hvac = HvacFactory.create(hass, self.options, self, self.observer)
    # self.spotprice = SpotPriceFactory.create(
    #     hub=self,
    #     observer=self.observer,
    #     system=PeaqSystem.PeaqHvac,
    #     test=False,
    #     is_active=True
    # )
    #
    # self.prognosis = WeatherPrognosis(hass, self.sensors.average_temp_outdoors, self.observer)
    # self.offset = OffsetFactory.create(self, observer=self.observer)


async def async_setup() -> None:
    pass


def _get_peaqev(hass):
    try:
        ret = hass.states.get("sensor.peaqev_threshold")
        if ret is not None:
            if ret.state:
                _LOGGER.debug("Discovered Peaqev-entities, will adhere to peak-shaving.")
                return True
        _LOGGER.debug("Unable to discover Peaqev-entities, will not adhere to peak-shaving.")
        return False
    except Exception as e:
        _LOGGER.debug(f"Unable to discover Peaqev-entities, will not adhere to peak-shaving. Exception {e}")
        return False
