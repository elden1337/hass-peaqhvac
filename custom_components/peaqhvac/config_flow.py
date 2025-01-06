"""Config flow for Peaq integration."""
from __future__ import annotations

import logging
from typing import Any, Optional
import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback

from custom_components.peaqhvac.configflow.config_flow_schemas import USER_SCHEMA, OPTIONAL_SCHEMA
from custom_components.peaqhvac.configflow.config_flow_validation import ConfigFlowValidation
from .const import DOMAIN  # pylint:disable=unused-import

_LOGGER = logging.getLogger(__name__)


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL
    OPTIONS = "options"
    data: Optional[dict[str, Any]]
    info: Optional[dict[str, Any]]

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Create the options flow."""
        return OptionsFlowHandler()

    async def async_step_user(self, user_input=None):
        """Invoked when a user initiates a flow via the user interface."""
        errors = {}
        if user_input is not None:
            self.info = await ConfigFlowValidation.validate_input_first(user_input)
            self.data = user_input
            return await self.async_step_optional()

        return self.async_show_form(
            step_id="user", data_schema=USER_SCHEMA, errors=errors, last_step=False
        )

    async def async_step_optional(self, user_input=None):
        errors = {}
        if user_input is not None:
            self.data.update(user_input)
            return self.async_create_entry(title=self.info["title"], data=self.data)

        return self.async_show_form(
            step_id="optional", data_schema=OPTIONAL_SCHEMA, errors=errors, last_step=True
        )


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Options flow handler."""
    def __init__(self) -> None:
        """Initialize options flow."""
        self._conf_app_id: str | None = None
        options = self.config_entry.options

    async def _get_existing_param(self, parameter: str, default_val: any):
        if parameter in self.config_entry.options.keys():
            return self.config_entry.options.get(parameter)
        if parameter in self.config_entry.data.keys():
            return self.config_entry.data.get(parameter)
        return default_val

    async def async_step_init(self, user_input=None):
        """Priceaware"""
        if user_input is not None:
            self.options.update(user_input)
            return self.async_create_entry(title="", data=self.options)

        _indoortemps = await self._get_existing_param("indoor_tempsensors", "")
        _outdoortemps = await self._get_existing_param("outdoor_tempsensors", "")
        _stopheatingtemp = await self._get_existing_param("outdoor_temp_stop_heating", 15)
        _nonhours_waterboost = await self._get_existing_param("non_hours_water_boost", [])
        _demandhours_waterboost = await self._get_existing_param("demand_hours_water_boost", [])
        _lowdm = await self._get_existing_param("low_degree_minutes", "-600")
        _verycoldtemp = await self._get_existing_param("very_cold_temp", "-12")
        _weather_entity = await self._get_existing_param("weather_entity", None)

        return self.async_show_form(
            step_id="init",
            last_step=True,
            data_schema=vol.Schema({
                vol.Optional("indoor_tempsensors", default=_indoortemps): cv.string,
                vol.Optional("outdoor_tempsensors", default=_outdoortemps): cv.string,
                vol.Optional("outdoor_temp_stop_heating", default=_stopheatingtemp): cv.positive_int,
                vol.Optional("demand_hours_water_boost", default=_demandhours_waterboost): cv.multi_select(
                    list(range(0, 24))),
                vol.Optional("non_hours_water_boost", default=_nonhours_waterboost): cv.multi_select(list(range(0, 24))),
                vol.Optional("low_degree_minutes", default=_lowdm): cv.string,
                vol.Optional("very_cold_temp", default=_verycoldtemp): cv.string,
                vol.Optional("weather_entity", default=_weather_entity): cv.string,
                })
        )
