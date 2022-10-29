import logging
from datetime import timedelta

from homeassistant.core import (
    HomeAssistant,
)
from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import (
    SUPPORT_TARGET_TEMPERATURE,
    HVACMode,
    HVACAction,
    PRESET_NONE,
    PRESET_ECO,
    PRESET_AWAY,
    SUPPORT_PRESET_MODE
)
from homeassistant.const import (
    TEMP_CELSIUS,
    ATTR_TEMPERATURE
)
from custom_components.peaqhvac.service.models.hvacmode import HvacMode as HvacModeInternal
import custom_components.peaqhvac.extensionmethods as ex
from custom_components.peaqhvac.const import DOMAIN, CLIMATE_SENSOR

_LOGGER = logging.getLogger(__name__)
SCAN_INTERVAL = timedelta(seconds=10)

async def async_setup_entry(hass : HomeAssistant, config, async_add_entities):
    hub = hass.data[DOMAIN]["hub"]

    devices = []
    device = PeaqClimate(
        hass,
        config.entry_id,
        hub,
        CLIMATE_SENSOR
    )

    devices.append(device)
    async_add_entities(devices)


class PeaqClimate(ClimateEntity):
    def __init__(self, hass, entry_id, hub, name):
        self._hass = hass
        self._entry_id = entry_id
        self._available = True
        self._hub = hub
        self._name = f"{hub.hubname} {name}"
        self._current_temperature = None
        self._target_temperature = None
        self._target_temperature_high = None
        self._target_temperature_low = None
        self._hvac_mode = HVACMode.AUTO
        self._preset_mode = PRESET_NONE

    @property
    def supported_features(self):
        return SUPPORT_TARGET_TEMPERATURE|SUPPORT_PRESET_MODE

    @property
    def name(self):
        return self._name

    @property
    def available(self):
        return self._available

    @property
    def unique_id(self):
        return f"{DOMAIN}_{self._entry_id}_{ex.nametoid(self._name)}"

    @property
    def temperature_unit(self):
        return TEMP_CELSIUS

    @property
    def current_temperature(self):
        return self._current_temperature

    @property
    def target_temperature(self):
        return self._target_temperature

    @property
    def target_temperature_high(self):
        return self._target_temperature_high

    @property
    def target_temperature_low(self):
        return self._target_temperature_low

    @property
    def hvac_mode(self):
        return self._hvac_mode

    @property
    def preset_mode(self):
        return self._preset_mode

    @property
    def hvac_modes(self):
        return [HVACMode.AUTO, HVACMode.OFF]

    @property
    def preset_modes(self):
        return [PRESET_NONE,PRESET_ECO,PRESET_AWAY]

    @property
    def min_temp(self):
        return 15.0

    @property
    def max_temp(self):
        return 27.0

    @property
    def hvac_action(self):
        if self._hub.sensors.peaq_enabled.value is False:
            return HVACAction.OFF
        else:
            match self._hub.hvac.hvac_mode:
                case HvacModeInternal.Heat:
                    return HVACAction.HEATING
                case HvacModeInternal.Idle:
                    return HVACAction.IDLE
                case _:
                    return HVACAction.OFF

    async def async_will_remove_from_hass(self):
        pass

    def set_temperature(self, **kwargs):
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            return
        self._hub.sensors.set_temp_indoors = temperature
        self._target_temperature = temperature

    def set_hvac_mode(self, hvac_mode):
        if hvac_mode == HVACMode.OFF:
            self._hub.sensors.peaq_enabled.value = False
        else:
            self._hub.sensors.peaq_enabled.value = True

    def set_preset_mode(self, preset_mode):
        if self._preset_mode == PRESET_AWAY and preset_mode != self._preset_mode:
            self._hub.sensors.set_temp_indoors += 2
        elif self._preset_mode != PRESET_AWAY and preset_mode == PRESET_AWAY:
            self._hub.sensors.set_temp_indoors -= 2
        self._preset_mode = preset_mode

    def update(self, event_time=None):
        try:
            current_temp = self._hub.sensors.average_temp_indoors.value
            target_temp = self._hub.sensors.set_temp_indoors.value
            target_low = self._hub.sensors.set_temp_indoors.min_tolerance
            target_high = self._hub.sensors.set_temp_indoors.max_tolerance
            self._available = True
        except Exception as e:
            _LOGGER.exception(f"Failed to update climate {self.unique_id}. {e}")
            self._available = False
            return
        self._current_temperature = current_temp
        self._target_temperature = target_temp
        self._target_temperature_high = target_high
        self._target_temperature_low = target_low
