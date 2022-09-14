from homeassistant.components.min_max.sensor import (
    MinMaxSensor, ATTR_MEAN
)
import custom_components.peaqhvac.extensionmethods as ex
from custom_components.peaqhvac.const import DOMAIN


class MinMaxSensor(MinMaxSensor):
    def __init__(
            self,
            hub,
            entry_id,
            name: str,
            listenerentities:list[str],
            sensortype: str = ATTR_MEAN,
            rounding_precision: int = 1
    ):
        super().init(
        unique_id = self.unique_id,
        entity_ids=listenerentities,
        sensor_type=sensortype,
        round_digits=rounding_precision
        )

    @property
    def unique_id(self):
        """Return a unique ID to use for this sensor."""
        return f"{DOMAIN}_{self._entry_id}_{ex.nametoid(self._attr_name)}"

    @property
    def device_info(self):
        """Return information to link this entity with the correct device."""
        return {"identifiers": {(DOMAIN, self._hub.hub_id)}}

"""
 - platform: min_max
      entity_ids:
      - sensor.lumi_lumi_weather_900a4b05_temperature
      - sensor.lumi_lumi_weather_36ef4405_temperature
      - sensor.temp_nibe_hall
      - sensor.lumi_lumi_weather_temperature
      name: "Medeltemp nere"
      type: mean
      round_digits: 1
    - platform: min_max
      entity_ids:
      - sensor.lumi_lumi_weather_74c34a05_temperature
      - sensor.lumi_lumi_weather_22df4005_temperature
      - sensor.tv_rum_sensor_temperature_corrected
      - sensor.lumi_lumi_weather_d6394105_temperature
      name: "Medeltemp uppe"
      type: mean
      round_digits: 1
    - platform: min_max
      entity_ids:
      - sensor.lumi_lumi_weather_900a4b05_temperature
      - sensor.lumi_lumi_weather_36ef4405_temperature
      - sensor.lumi_lumi_weather_74c34a05_temperature
      - sensor.lumi_lumi_weather_22df4005_temperature
      - sensor.temp_nibe_hall
      - sensor.tv_rum_sensor_temperature_corrected
      - sensor.lumi_lumi_weather_temperature
      - sensor.lumi_lumi_weather_d6394105_temperature
      name: "Medeltemp hemma"
      type: mean
      round_digits: 1
"""