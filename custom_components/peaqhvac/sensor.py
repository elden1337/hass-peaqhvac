"""Platform for sensor integration."""
import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import (
    HomeAssistant,
)

from .const import DOMAIN, TRENDSENSOR_INDOORS, TRENDSENSOR_OUTDOORS, AVERAGESENSOR_INDOORS, AVERAGESENSOR_OUTDOORS
import custom_components.peaqhvac.extensionmethods as ex
from .sensors.min_maxsensor import AverageSensor
from .sensors.trendsensor import TrendSensor
from .sensors.gradientsensor import GradientSensor

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

    ret.append(AverageSensor(
        hub=hub,
        entry_id=config.entry_id,
        name=AVERAGESENSOR_INDOORS
    ))
    ret.append(AverageSensor(
        hub=hub,
        entry_id=config.entry_id,
        name=AVERAGESENSOR_OUTDOORS
    ))

    ret.append(GradientSensor(
        hub,
        hass,
        config.entry_id,
        name="temperature rising indoors",
        listenerentity=ex.nametoid(f"sensor.{DOMAIN} {AVERAGESENSOR_INDOORS}"),
        sample_duration=7200,
        max_samples=120,
        min_gradient=0.0008,
        device_class="heat")
    )
    ret.append(GradientSensor(
        hub,
        hass,
        config.entry_id,
        name="temperature rising outdoors",
        listenerentity=ex.nametoid(f"sensor.{DOMAIN} {AVERAGESENSOR_OUTDOORS}"),
        sample_duration=7200,
        max_samples=120,
        min_gradient=0.0008,
        device_class="heat")
    )

    ret.append(TrendSensor(hub, config.entry_id, TRENDSENSOR_OUTDOORS))
    ret.append(TrendSensor(hub, config.entry_id, TRENDSENSOR_INDOORS))

    return ret