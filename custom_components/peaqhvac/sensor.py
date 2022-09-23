"""Platform for sensor integration."""
import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import (
    HomeAssistant,
)

from .const import DOMAIN, TRENDSENSOR_INDOORS, TRENDSENSOR_OUTDOORS, AVERAGESENSOR_INDOORS, AVERAGESENSOR_OUTDOORS, DEMANDSENSORS
from .sensors.min_maxsensor import AverageSensor
from .sensors.offsetsensor import OffsetSensor
from .sensors.peaqsensor import PeaqSensor
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

    ret.append(TrendSensor(hub, config.entry_id, TRENDSENSOR_OUTDOORS))
    ret.append(TrendSensor(hub, config.entry_id, TRENDSENSOR_INDOORS))

    ret.append(OffsetSensor(hub, config.entry_id, "calculated hvac offset"))

    for key in DEMANDSENSORS:
        ret.append(PeaqSensor(hub, config.entry_id, key, DEMANDSENSORS[key]))

    return ret