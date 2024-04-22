from custom_components.peaqhvac import DOMAIN


async def async_setup_services(hass, hub) -> None:
    async def servicehandler_enable(call):  # pylint:disable=unused-argument
        await hub.call_enable_peaq()


    async def servicehandler_disable(call):  # pylint:disable=unused-argument
        await hub.call_disable_peaq()


    async def servicehandler_set_mode(call):
        mode = call.data.get("mode")
        await hub.call_set_mode(mode)


    async def servicehandler_boost_water(call):
        target = call.data.get("targettemp")
        if 10 < target < 60:
            hub.observer.broadcast("water boost start", target)


    hass.services.async_register(DOMAIN, "enable", servicehandler_enable)
    hass.services.async_register(DOMAIN, "disable", servicehandler_disable)
    hass.services.async_register(DOMAIN, "set_mode", servicehandler_set_mode)
    hass.services.async_register(DOMAIN, "boost_water", servicehandler_boost_water)