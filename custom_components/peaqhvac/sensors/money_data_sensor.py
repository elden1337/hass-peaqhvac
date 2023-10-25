from __future__ import annotations

from typing import TYPE_CHECKING
import logging

from custom_components.peaqhvac import DOMAIN
from custom_components.peaqhvac.extensionmethods import nametoid
from custom_components.peaqhvac.sensors.const import MONEYCONTROLS

if TYPE_CHECKING:
    from custom_components.peaqhvac.service.hub.hub import Hub

from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.components.sensor import SensorEntity

_LOGGER = logging.getLogger(__name__)


class PeaqMoneyDataSensor(SensorEntity, RestoreEntity):
    """Holding spotprice average data"""

    def __init__(self, hub: Hub, entry_id):
        name = f"{hub.hubname} {AVERAGE_SPOTPRICE_DATA}"
        #super().__init__(hub, name, entry_id)

        self.hub = hub
        self._entry_id = entry_id
        self._attr_name = name
        self._state = None
        self._average_spotprice_data = {}

    @property
    def icon(self) -> str:
        return "mdi:database-outline"

    async def async_update(self) -> None:
        try:
            ret = self.hub.spotprice.average_data
        except:
            ret = None
        if ret is not None:
            if len(ret):
                self._state = "on"
                if ret != self._average_spotprice_data:
                    _diff = self.diff_dicts(self._average_spotprice_data, ret)
                    _LOGGER.debug(f"dict was changed: added: {_diff[0]}, removed: {_diff[1]}")
                self._average_spotprice_data = ret
                self.hub.spotprice.converted_average_data = True

    @staticmethod
    def diff_dicts(dict1, dict2):
        added = {}
        removed = {}

        for key in dict2:
            if key not in dict1:
                added[key] = dict2[key]

        for key in dict1:
            if key not in dict2:
                removed[key] = dict1[key]

        return added, removed

    @property
    def extra_state_attributes(self) -> dict:
        attr_dict = {"Spotprice average data":   self._average_spotprice_data }
        return attr_dict

    async def async_added_to_hass(self):
        state = await super().async_get_last_state()
        _LOGGER.debug("last state of %s = %s", self._attr_name, state)
        if state:
            self._state = "on"
            data = state.attributes.get("Spotprice average data", [])
            if len(data):
                self.hub.spotprice.converted_average_data = True
                await self.hub.spotprice.async_import_average_data(data)
                self._average_spotprice_data = self.hub.spotprice.average_data

    @property
    def device_info(self):
        return {
            "identifiers":  {(DOMAIN, self.hub.hub_id, MONEYCONTROLS)},
            "name":         f"{DOMAIN} {MONEYCONTROLS}",
            "sw_version":   1,
            "manufacturer": "Peaq systems",
        }

    @property
    def unique_id(self):
        """Return a unique ID to use for this sensor."""
        return f"{DOMAIN}_{self._entry_id}_{nametoid(self._attr_name)}"
