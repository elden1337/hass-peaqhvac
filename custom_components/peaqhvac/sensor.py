"""Platform for sensor integration."""
import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import (
    HomeAssistant,
)

from .const import DOMAIN
from .sensors.min_maxsensor import MinMaxSensor
from .sensors.trendsensor import TrendSensor

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(seconds=4)

async def async_setup_entry(hass : HomeAssistant, config: ConfigEntry, async_add_entities):
    """Add sensors for passed config_entry in HA."""

    hub = hass.data[DOMAIN]["hub"]
    peaqsensors = await _gather_sensors(hub, config, hass)
    async_add_entities(peaqsensors, update_before_add = True)

async def _gather_sensors(hub, config, hass) -> list:
    ret = []

    #waterheatersensor
    #hvacsensor

    #temperature input_numbersensor
    # tolerance (-5 - 5) input_numbersensor

    """sensor.peaqhvac_average_temperature_indoors"""
    ret.append(MinMaxSensor(
        hub,
        config.entry_id,
        name="average temperature indoors",
        listenerentities=hub.sensors.temp_sensors_indoor,
        sensortype="mean",
        rounding_precision=1
    ))

    """sensor.peaqhvac_average_temperature_outdoors"""
    ret.append(MinMaxSensor(
        hub,
        config.entry_id,
        name="average temperature outdoors",
        listenerentities=hub.sensors.temp_sensors_outdoor,
        sensortype="mean",
        rounding_precision=1
    ))

    ret.append(TrendSensor(
        hub,
        hass,
        config.entry_id,
        name="temperature trend indoors",
        listenerentity="sensor.peaqhvac_average_temperature_indoors",
        sample_duration=7200,
        max_samples=120,
        min_gradient=0.0008,
        device_class="heat")
    )
    ret.append(TrendSensor(
        hub,
        hass,
        config.entry_id,
        name="temperature trend outdoors",
        listenerentity="sensor.peaqhvac_average_temperature_outdoors",
        sample_duration=7200,
        max_samples=120,
        min_gradient=0.0008,
        device_class="heat")
    )

    return ret