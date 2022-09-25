"""Platform for sensor integration."""
import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import (
    HomeAssistant,
)

from .const import DOMAIN, TRENDSENSORS, AVERAGESENSORS, DEMANDSENSORS
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

    ret.append(OffsetSensor(hub, config.entry_id, "calculated hvac offset"))
    for a in AVERAGESENSORS:
        ret.append(AverageSensor(hub, config.entry_id, a))
    for key in TRENDSENSORS:
        ret.append(TrendSensor(hub, config.entry_id, key, TRENDSENSORS[key]))
    for key in DEMANDSENSORS:
        ret.append(PeaqSensor(hub, config.entry_id, key, DEMANDSENSORS[key]))

    return ret