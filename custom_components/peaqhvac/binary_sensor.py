from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.core import HomeAssistant

from .const import (
    DOMAIN, PEAQENABLED)


async def async_setup_entry(hass: HomeAssistant, config_entry, async_add_entities):
    hub = hass.data[DOMAIN]["hub"]

    peaqsensors = []

    peaqsensors.append(PeaqBinarySensorEnabled(hub))
    async_add_entities(peaqsensors)


class PeaqBinarySensorEnabled(BinarySensorEntity):
    """The binary sensor for peaq being enabled or disabled"""
    def __init__(self, hub) -> None:
        """Initialize a Peaq Binary sensor."""
        self._attr_name = f"{hub.hubname} {PEAQENABLED}"
        self._hub = hub
        self._attr_device_class = "none"

    @property
    def unique_id(self):
        """The unique id used by Home Assistant"""
        return f"{DOMAIN.lower()}_{self._attr_name}"

    @property
    def device_info(self):
        return {"identifiers": {(DOMAIN, self._hub.hub_id)}}

    @property
    def is_on(self) -> bool:
        return self._hub.sensors.peaq_enabled.value
