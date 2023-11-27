"""Platform for sensor integration."""
import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import AVERAGESENSORS, DEMANDSENSORS, DOMAIN, NEXT_WATER_START, LATEST_WATER_BOOST, \
    TRENDSENSOR_DM, TRENDSENSOR_OUTDOORS, TRENDSENSOR_INDOORS
from .sensors.min_maxsensor import AverageSensor
from .sensors.money_data_sensor import PeaqMoneyDataSensor
from .sensors.offsetsensor import OffsetSensor
from .sensors.peaqsensor import PeaqSensor
from .sensors.simple_money_sensor import PeaqSimpleMoneySensor
from .sensors.simple_sensor import PeaqSimpleSensor
from .sensors.trendsensor import TrendSensor

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(seconds=4)


async def async_setup_entry(
    hass: HomeAssistant, config: ConfigEntry, async_add_entities
):
    """Add sensors for passed config_entry in HA."""

    hub = hass.data[DOMAIN]["hub"]
    peaqsensors = await _gather_sensors(hub, config, hass)
    async_add_entities(peaqsensors, update_before_add=True)




async def _gather_sensors(hub, config, hass) -> list:
    TRENDSENSORS = [
        {
            "name":   TRENDSENSOR_INDOORS,
            "sensor": hub.sensors.temp_trend_indoors,
            "icon":   "mdi:home-thermometer",
            "unit":   "°C/h",
        },
        {
            "name":   TRENDSENSOR_OUTDOORS,
            "sensor": hub.sensors.temp_trend_outdoors,
            "icon":   "mdi:sun-thermometer",
            "unit":   "°C/h",
        },
        {
            "name":   TRENDSENSOR_DM,
            "sensor": hub.sensors.dm_trend,
            "icon":   "mdi:hvac",
            "unit":   "DM/h",
        }
    ]


    ret = []

    ret.append(OffsetSensor(hub, config.entry_id, "calculated hvac offset"))
    for a in AVERAGESENSORS:
        ret.append(AverageSensor(hub, config.entry_id, a))
    for sensor in TRENDSENSORS:
        ret.append(TrendSensor(
            hub=hub,
            entry_id=config.entry_id,
            name=sensor["name"],
            icon=sensor["icon"],
            unit_of_measurement=sensor["unit"],
            sensor=sensor["sensor"]))
    for key in DEMANDSENSORS:
        ret.append(PeaqSensor(hub, config.entry_id, key, DEMANDSENSORS[key]))

    ret.append(PeaqSimpleSensor(hub, config.entry_id, "next water start", NEXT_WATER_START, "mdi:clock-start"))
    ret.append(PeaqSimpleSensor(hub, config.entry_id, "latest water boost", LATEST_WATER_BOOST, "mdi:clock-end"))

    if not hub.peaqev_discovered:
        simplesensors = [("Average price this month", "average_month"),
                         ("Average price 7 days", "average_weekly"),
                         ("Average price 30 days", "average_30"),
                         ("Average price 3 days", "average_three_days")]

        for name, attr in simplesensors:
            ret.append(
                PeaqSimpleMoneySensor(
                    hub, config.entry_id, name, attr)
            )
            _LOGGER.debug(f"Setting up sensor for {name} with attr {attr}")

        ret.append(PeaqMoneyDataSensor(hub, config.entry_id))

    return ret
