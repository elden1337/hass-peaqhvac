"""The peaqhvac integration."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from custom_components.peaqhvac.service.hub.hub import Hub

from .const import DOMAIN, HVACBRAND_NIBE, LISTENER_FN_CLOSE, PLATFORMS
from .service.models.config_model import ConfigModel

_LOGGER = logging.getLogger(__name__)

async def async_get_existing_param(conf, parameter: str, default_val: any):
    return conf.options.get(parameter, conf.data.get(parameter, default_val))

async def async_setup_entry(hass: HomeAssistant, config: ConfigEntry) -> bool:
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][config.entry_id] = config.data

    huboptions = ConfigModel()

    huboptions.indoor_tempsensors = huboptions.set_sensors_from_string(
        await async_get_existing_param(config, "indoor_tempsensors", "")
    )
    huboptions.outdoor_tempsensors = huboptions.set_sensors_from_string(
        await async_get_existing_param(config, "outdoor_tempsensors", "")
    )
    huboptions.heating_options.outdoor_temp_stop_heating = await async_get_existing_param(config, "outdoor_temp_stop_heating", 15)
    huboptions.heating_options.non_hours_water_boost = await async_get_existing_param(config, "non_hours_water_boost",[7, 11, 12, 15, 16, 17,23])
    huboptions.heating_options.demand_hours_water_boost = await async_get_existing_param(config, "demand_hours_water_boost",[])

    huboptions.heating_options.low_degree_minutes = int((await async_get_existing_param(config, "low_degree_minutes","-600")).replace(" ", ""))
    huboptions.heating_options.very_cold_temp = int((await async_get_existing_param(config, "very_cold_temp","-12")).replace(" ", ""))
    huboptions.systemid = config.data["systemid"]

    huboptions.hvacbrand = huboptions.set_hvacbrand(
        HVACBRAND_NIBE
    )  # todo:move to proper dropdown in configflow


    hub = Hub(hass, huboptions)

    hass.data[DOMAIN]["hub"] = hub

    await hub.async_setup()

    async def servicehandler_enable(call):  # pylint:disable=unused-argument
        await hub.call_enable_peaq()

    async def servicehandler_disable(call):  # pylint:disable=unused-argument
        await hub.call_disable_peaq()

    async def servicehandler_set_mode(call):
        mode = call.data.get("mode")
        await hub.call_set_mode(mode)

    async def servicehandler_boost_water(call):
        timeout_in_minutes = call.data.get("timeout")
        if 10 < timeout_in_minutes < 60:
            timeout = timeout_in_minutes * 60
            hub.observer.broadcast("water boost start", timeout)

    hass.services.async_register(DOMAIN, "enable", servicehandler_enable)
    hass.services.async_register(DOMAIN, "disable", servicehandler_disable)
    hass.services.async_register(DOMAIN, "set_mode", servicehandler_set_mode)
    hass.services.async_register(DOMAIN, "boost_water", servicehandler_boost_water)

    await hass.config_entries.async_forward_entry_setups(config, PLATFORMS)

    undo_listener = config.add_update_listener(config_entry_update_listener)

    hass.data[DOMAIN][config.entry_id] = {
        LISTENER_FN_CLOSE: undo_listener,
    }
    return True


async def config_entry_update_listener(hass: HomeAssistant, entry: ConfigEntry):
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok

async def async_update_entry(hass: HomeAssistant, config_entry: ConfigEntry):
    """Reload Peaqev component when options changed."""
    _LOGGER.debug("Reloading PeaqHvac component")
    return await hass.config_entries.async_reload(config_entry.entry_id)
