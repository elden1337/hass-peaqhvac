from __future__ import annotations

from typing import TYPE_CHECKING

from custom_components.peaqhvac import DOMAIN
from homeassistant.components.sensor import SensorEntity
from homeassistant.components.sensor import SensorDeviceClass

from custom_components.peaqhvac.extensionmethods import nametoid
from custom_components.peaqhvac.sensors.const import MONEYCONTROLS

if TYPE_CHECKING:
    from custom_components.peaqhvac.service.hub.hub import Hub

import logging

_LOGGER = logging.getLogger(__name__)



class PeaqSimpleMoneySensor(SensorEntity):
    device_class = SensorDeviceClass.MONETARY

    def __init__(self, hub: Hub, entry_id, sensor_name: str, caller_attribute: str):
        name = f"{hub.hubname} {sensor_name}"
        #super().__init__(hub, name, entry_id)

        self._attr_name = name
        self._entry_id = entry_id
        self.hub = hub
        self._state = None
        self._caller_attribute = caller_attribute
        self._use_cent = None
        self._attr_unit_of_measurement = None

    @property
    def state(self):
        return self._state

    @property
    def icon(self) -> str:
        return "mdi:car-clock"

    @property
    def unit_of_measurement(self):
        return self._attr_unit_of_measurement

    async def async_update(self) -> None:
        self._use_cent = self.hub.spotprice.use_cent
        self._attr_unit_of_measurement = getattr(self.hub.spotprice, "currency")
        ret = getattr(self.hub.spotprice, self._caller_attribute)
        if ret is not None:
            self._state = ret if not self._use_cent else ret / 100

    @property
    def extra_state_attributes(self) -> dict:
        return {
            "Use Cent": self._use_cent,
            "Price Source": self.hub.spotprice.source
        }

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self.hub.hub_id, MONEYCONTROLS)},
            "name": f"{DOMAIN} {MONEYCONTROLS}",
            "sw_version": 1,
            "manufacturer": "Peaq systems",
        }

    @property
    def unique_id(self):
        """Return a unique ID to use for this sensor."""
        return f"{DOMAIN}_{self._entry_id}_{nametoid(self._attr_name)}"

