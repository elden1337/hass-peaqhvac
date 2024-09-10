import logging
from datetime import timedelta

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.restore_state import RestoreEntity

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)
SCAN_INTERVAL = timedelta(seconds=4)

ENABLED = "enabled"
AWAYMODE = "away mode"
CONTROL_WATER = "control water"
CONTROL_HEAT = "control heat"
CONTROL_VENTILATION = "control ventilation"

async def async_setup_entry(
    hass: HomeAssistant, config_entry, async_add_entities
):  # pylint:disable=unused-argument
    hub = hass.data[DOMAIN]["hub"]

    switches = [
        {"name": ENABLED, "entity": "_enabled"},
        {"name": CONTROL_WATER, "entity": "control_water"},
        {"name": CONTROL_HEAT, "entity": "control_heat"},
        {"name": CONTROL_VENTILATION, "entity": "control_ventilation"},
    ]

    async_add_entities(PeaqSwitch(s, hub) for s in switches)


class PeaqSwitch(SwitchEntity, RestoreEntity):
    def __init__(self, switch, hub) -> None:
        """Initialize a PeaqSwitch."""
        self._switch = switch
        self._attr_name = f"{hub.hubname} {self._switch['name']}"
        self._hub = hub
        self._attr_device_class = "none"
        self._state = None

    @property
    def unique_id(self):
        """The unique id used by Home Assistant"""
        return f"{DOMAIN.lower()}_{self._attr_name}"

    @property
    def device_info(self):
        return {"identifiers": {(DOMAIN, self._hub.hub_id)}}

    @property
    def is_on(self) -> bool:
        if self._switch["name"] == ENABLED:
            return self._hub.sensors.peaqhvac_enabled.value
        elif self._switch["name"] == CONTROL_WATER:
            return self._hub.hvac.water_heater.control_module
        elif self._switch["name"] == CONTROL_HEAT:
            return self._hub.hvac.house_heater.control_module
        elif self._switch["name"] == CONTROL_VENTILATION:
            return self._hub.hvac.house_ventilation.control_module

    @property
    def state(self) -> str:
        return self._state

    @state.setter
    def state(self, value):
        self._state = value

    def turn_on(self):
        if self._switch["name"] == ENABLED:
            self._hub.sensors.peaqhvac_enabled.value = True
        elif self._switch["name"] == CONTROL_WATER:
            self._hub.hvac.water_heater.control_module = True
        elif self._switch["name"] == CONTROL_HEAT:
            self._hub.hvac.house_heater.control_module = True
        elif self._switch["name"] == CONTROL_VENTILATION:
            self._hub.hvac.house_ventilation.control_module = True

    def turn_off(self):
        if self._switch["name"] == ENABLED:
            self._hub.sensors.peaqhvac_enabled.value = False
        elif self._switch["name"] == CONTROL_WATER:
            self._hub.hvac.water_heater.control_module = False
        elif self._switch["name"] == CONTROL_HEAT:
            self._hub.hvac.house_heater.control_module = False
        elif self._switch["name"] == CONTROL_VENTILATION:
            self._hub.hvac.house_ventilation.control_module = False

    def update(self):
        new_state = None
        if self._switch["name"] == ENABLED:
            new_state = self._hub.sensors.peaqhvac_enabled.value
        elif self._switch["name"] == CONTROL_WATER:
            new_state = self._hub.hvac.water_heater.control_module
        elif self._switch["name"] == CONTROL_HEAT:
            new_state = self._hub.hvac.house_heater.control_module
        elif self._switch["name"] == CONTROL_VENTILATION:
            new_state = self._hub.hvac.house_ventilation.control_module
        self.state = "on" if new_state is True else "off"

    async def async_added_to_hass(self):
        state = await super().async_get_last_state()
        if state:
            self.state = state.state
            if self._switch["name"] == ENABLED:
                self._hub.sensors.peaqhvac_enabled.value = state.state
            elif self._switch["name"] == CONTROL_WATER:
                self._hub.hvac.water_heater.control_module = state.state
            elif self._switch["name"] == CONTROL_HEAT:
                self._hub.hvac.house_heater.control_module = state.state
            elif self._switch["name"] == CONTROL_VENTILATION:
                self._hub.hvac.house_ventilation.control_module = state.state
        else:
            self.update()
