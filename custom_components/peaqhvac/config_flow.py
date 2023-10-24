"""Config flow for Peaq integration."""
from __future__ import annotations

import logging
# from homeassistant.core import callback
from typing import Any, Optional

from homeassistant import config_entries

from custom_components.peaqhvac.configflow.config_flow_schemas import \
    USER_SCHEMA
from custom_components.peaqhvac.configflow.config_flow_validation import \
    ConfigFlowValidation

from .const import DOMAIN  # pylint:disable=unused-import

_LOGGER = logging.getLogger(__name__)


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL
    OPTIONS = "options"
    data: Optional[dict[str, Any]]
    info: Optional[dict[str, Any]]


    async def async_step_user(self, user_input=None):
        """Invoked when a user initiates a flow via the user interface."""
        errors = {}
        if user_input is not None:
            self.info = await ConfigFlowValidation.validate_input_first(user_input)
            self.data = user_input
            return self.async_create_entry(title=self.info["title"], data=self.data)

        return self.async_show_form(
            step_id="user", data_schema=USER_SCHEMA, errors=errors, last_step=True
        )

