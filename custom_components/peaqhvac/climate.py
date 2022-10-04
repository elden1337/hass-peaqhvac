#
# import logging
# from homeassistant.components.climate import (
#     ENTITY_ID_FORMAT,
#     ClimateEntity,
#     ClimateEntityFeature,
#     HVACAction,
#     HVACMode,
# )
# from homeassistant.const import (
#     ATTR_TEMPERATURE,
#     CONF_NAME,
#     STATE_UNAVAILABLE,
#     STATE_UNKNOWN,
#     TEMP_CELSIUS,
# )
# from homeassistant.helpers.restore_state import RestoreEntity
# import custom_components.peaqhvac.extensionmethods as ex
# from custom_components.peaqhvac.const import DOMAIN
#
# _LOGGER = logging.getLogger(__name__)
#
# DEFAULT_THERMOSTAT_TEMPERATURE = 20
#
# async def async_setup_entry(
#     hass: HomeAssistant, entry: ConfigEntry, async_add_entities
# ):
#     """Set up the climate device based on a config entry."""
#     data: NibeData = hass.data[DATA_NIBE_ENTRIES][entry.entry_id]
#     uplink = data.uplink
#     systems = data.systems
#
#     entities = []
#
#     async def add_active(system: NibeSystem):
#         climates = await get_active_climate(uplink, system.system_id)
#         for climate in climates.values():
#             entities.append(NibeClimateSupply(system, climate))
#             entities.append(NibeClimateRoom(system, climate))
#
#     for system in systems.values():
#         thermostats = system.config[CONF_THERMOSTATS]
#         for thermostat_id, thermostat_config in thermostats.items():
#             entities.append(
#                 NibeThermostat(
#                     system,
#                     thermostat_id,
#                     thermostat_config.get(CONF_NAME),
#                     thermostat_config.get(CONF_CURRENT_TEMPERATURE),
#                     thermostat_config.get(CONF_VALVE_POSITION),
#                     thermostat_config.get(CONF_CLIMATE_SYSTEMS),
#                 )
#             )
#
#     #await asyncio.gather(*[add_active(system) for system in systems.values()])
#
#     async_add_entities(entities, True)
#
# class PeaqThermostat(ClimateEntity, RestoreEntity):
#     def __init__(
#         self,
#         name,
#         hub,
#         current_temperature_id
#     ):
#         """Init."""
#         self._attr_name = name
#         self._hub = hub
#         self._attr_hvac_mode = HVACMode.OFF
#         self._attr_hvac_modes = [HVACMode.OFF, HVACMode.HEAT_COOL, HVACMode.AUTO]
#         self._attr_hvac_action = None
#         #self._attr_supported_features = ClimateEntityFeature.TARGET_TEMPERATURE
#
#         self._attr_target_temperature_step = 0.5
#         self._current_temperature_id = current_temperature_id
#         self._current_temperature: float | None = None
#         self._attr_temperature_unit = TEMP_CELSIUS
#         self._attr_should_poll = False
#         self._target_temperature = DEFAULT_THERMOSTAT_TEMPERATURE
#
#
#     async def async_added_to_hass(self):
#         await super().async_added_to_hass()
#         state = await super().async_get_last_state()
#         if state:
#             self._current_temperature = state.state
#
#     # @property
#     # def extra_state_attributes(self):
#     #     """Return extra state."""
#     #     data = OrderedDict()
#     #     data[ATTR_VALVE_POSITION] = self._valve_position
#     #     data[ATTR_TARGET_TEMPERATURE] = self._target_temperature
#     #     return data
#
#     @property
#     def current_temperature(self):
#         return self._current_temperature
#
#     @property
#     def target_temperature(self):
#         if self._attr_hvac_mode == HVACMode.HEAT_COOL:
#             return self._target_temperature
#         else:
#             return None
#
#     @property
#     def device_info(self):
#         return {
#             "identifiers":  {(DOMAIN, self._hub.hub_id)},
#             "name":         self._attr_name,
#             "sw_version":   1,
#             "manufacturer": "Peaq systems",
#         }
#
#     @property
#     def unique_id(self):
#         """Return a unique ID to use for this sensor."""
#         return f"{DOMAIN}_{self._entry_id}_{ex.nametoid(self._attr_name)}"
#
#     def _update_current_temperature(self, state: State | None):
#         if state is None:
#             return
#         try:
#             if state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
#                 self._current_temperature = None
#             else:
#                 self._current_temperature = float(state.state)
#         except ValueError as ex:
#             self._current_temperature = None
#             _LOGGER.error("Unable to update from sensor: %s", ex)
#
#     async def async_set_hvac_mode(self, hvac_mode: str):
#         """Set operation mode."""
#         if hvac_mode in self._attr_hvac_modes:
#             self._attr_hvac_mode = hvac_mode
#         else:
#             _LOGGER.error("Unrecognized hvac mode: %s", hvac_mode)
#             return
#         await self._async_publish_update()
#
#     async def async_set_temperature(self, **kwargs):
#         """Set new target temperature."""
#         temperature = kwargs.get(ATTR_TEMPERATURE)
#         if temperature is None:
#             return
#         self._target_temperature = temperature
#         await self._async_publish_update()
#
#     async def _async_publish_update(self):
#         self.hass.add_job(self._async_publish())
#         await self.async_update_ha_state()
#
#     async def _async_publish(self, time=None):
#         def scaled(value, multi=10):
#             if value is None:
#                 return None
#             else:
#                 return round(value * multi)
#
#         if self._attr_hvac_mode == HVACMode.HEAT_COOL:
#             actual = scaled(self._current_temperature)
#             target = scaled(self._target_temperature)
#         elif self._attr_hvac_mode == HVACMode.AUTO:
#             actual = scaled(self._current_temperature)
#             target = None
#         else:
#             actual = None
#             target = None
#
#         data: SetThermostatModel = {
#             "name": self._attr_name,
#             "actualTemp": actual,
#             "targetTemp": target,
#         }
#
#         _LOGGER.debug(f"Publish thermostat {data}")
#         await self._uplink.post_smarthome_thermostats(self._system_id, data)
#
#     async def async_update(self):
#         """Explicitly update thermostat state."""
#         _LOGGER.debug(f"Update thermostat {self.name}")