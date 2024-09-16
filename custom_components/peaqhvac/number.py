from __future__ import annotations

import logging

from homeassistant.components.number import NumberEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.restore_state import RestoreEntity
from peaqevcore.common.models.observer_types import ObserverTypes

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

TOLERANCE = "Tolerance"


async def async_setup_entry(
    hass: HomeAssistant, config_entry, async_add_entities
):  # pylint:disable=unused-argument
    hub = hass.data[DOMAIN]["hub"]

    inputnumbers = [{"name": TOLERANCE, "entity": "_tolerance"}]

    async_add_entities(PeaqNumber(i, hub) for i in inputnumbers)


class PeaqNumber(NumberEntity, RestoreEntity):
    def __init__(self, number, hub) -> None:
        self._number = number
        self._attr_name = f"{hub.hubname} {self._number['name']}"
        self._hub = hub
        self._attr_device_class = None
        self._state = None

    @property
    def native_max_value(self) -> float:
        return 10

    @property
    def native_min_value(self) -> float:
        return 1

    @property
    def native_step(self) -> float:
        return 1.0

    @property
    def native_value(self) -> float | None:
        return self._state

    @property
    def mode(self) -> str:
        return "slider"

    def set_native_value(self, value: float) -> None:
        self._state = value
        self._hub.options.hvac_tolerance = int(float(self._state))

    async def async_added_to_hass(self):
        state = await super().async_get_last_state()
        if state:
            self.set_native_value(float(state.state))
        else:
            self.set_native_value(3)
