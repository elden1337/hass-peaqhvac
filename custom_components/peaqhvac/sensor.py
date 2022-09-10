"""Platform for sensor integration."""
import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import (
    HomeAssistant,
)

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(seconds=4)

async def async_setup_entry(hass : HomeAssistant, config: ConfigEntry, async_add_entities):
    """Add sensors for passed config_entry in HA."""

    hub = hass.data[DOMAIN]["hub"]
    peaqsensors = await _gather_sensors(hub, config)
    async_add_entities(peaqsensors, update_before_add = True)



async def _gather_sensors(hub, config) -> list:
    ret = []

    #waterheatersensor
    #hvacsensor

    #temperature input_numbersensor
    # tolerance (-5 - 5) input_numbersensor

    #avgtempsensor (with max and min as attributes, based on the list of tempsensors from config)
    #tempfalling indoors sensor
    #tempfalling outdoors sensor


    ret.append(PeaqAmpSensor(hub, config.entry_id))
    ret.append(PeaqSensor(hub, config.entry_id))
    ret.append(PeaqThresholdSensor(hub, config.entry_id))
    ret.append(PeaqSessionSensor(hub, config.entry_id))
    ret.append(PeaqSessionCostSensor(hub, config.entry_id))

    if hub.options.powersensor_includes_car is True:
        ret.append(PeaqHousePowerSensor(hub, config.entry_id))
    else:
        ret.append(PeaqPowerSensor(hub, config.entry_id))

    if hub.options.peaqev_lite is False:
        average_delta = 2 if hub.sensors.locale.data.is_quarterly(hub.sensors.locale.data) else 5
        ret.append(PeaqAverageSensor(hub, config.entry_id, AVERAGECONSUMPTION, timedelta(minutes=average_delta)))
        ret.append(PeaqAverageSensor(hub, config.entry_id, AVERAGECONSUMPTION_24H, timedelta(hours=24)))
        ret.append(PeaqPredictionSensor(hub, config.entry_id))

    if hub.options.price.price_aware is True:
        ret.append(PeaqMoneySensor(hub, config.entry_id))
    return ret