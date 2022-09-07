"""The peaqev integration."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from custom_components.peaqhvac.service.hub import Hub

from .const import (
    DOMAIN,
    PLATFORMS, LISTENER_FN_CLOSE
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, config: ConfigEntry) -> bool:
    """Set up Peaq"""

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][config.entry_id] = config.data

    configinputs = {}

    configinputs["tolerance"] = config.data["tolerance"]
    configinputs["tempsensors"] = config.data["tempsensors"]

    hub = Hub(hass, configinputs)

    hass.data[DOMAIN]["hub"] = hub

    async def servicehandler_enable(call): # pylint:disable=unused-argument
        await hub.call_enable_peaq()

    async def servicehandler_disable(call): # pylint:disable=unused-argument
        await hub.call_disable_peaq()

    hass.services.async_register(DOMAIN, "enable", servicehandler_enable)
    hass.services.async_register(DOMAIN, "disable", servicehandler_disable)

    hass.config_entries.async_setup_platforms(config, PLATFORMS)

    undo_listener = config.add_update_listener(config_entry_update_listener)

    hass.data[DOMAIN][config.entry_id] = {
        LISTENER_FN_CLOSE: undo_listener,
    }
    return True

async def config_entry_update_listener(hass: HomeAssistant, entry: ConfigEntry):
    await hass.config_entries.async_reload(entry.entry_id)

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
