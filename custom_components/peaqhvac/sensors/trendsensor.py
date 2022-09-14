from homeassistant.components.trend.binary_sensor import (
    SensorTrend, ATTR_MEAN
)
import custom_components.peaqhvac.extensionmethods as ex
from custom_components.peaqhvac.const import DOMAIN

class TrendSensor(SensorTrend):
    def __init__(
            self,
            hub,
            hass,
            entry_id,
            name: str,
            listenerentity:str,
            sample_duration: int,
            max_samples: int,
            min_gradient: float,
            device_class: str
    ):
        self._entry_id = entry_id
        self._attr_name = f"{hub.hubname} {name}"
        self._attr_device_class = "none"

        super().init(
            hass=hass,
            #device_id,
            #friendly_name,
            entity_id=listenerentity,
            #attribute,
            device_class=device_class,
            invert=False,
            max_samples=max_samples,
            min_gradient=min_gradient,
            sample_duration=sample_duration
        )

        self._hub = hub
        self._state = 0

    @property
    def unique_id(self):
        """Return a unique ID to use for this sensor."""
        return f"{DOMAIN}_{self._entry_id}_{ex.nametoid(self._attr_name)}"

    @property
    def device_info(self):
        """Return information to link this entity with the correct device."""
        return {"identifiers": {(DOMAIN, self._hub.hub_id)}}

"""
 - platform: trend
      sensors:
       temp_trend_indoors:
         entity_id: sensor.medeltemp_hemma
         sample_duration: 7200
         max_samples: 120
         min_gradient: 0.0008
         device_class: heat
"""


