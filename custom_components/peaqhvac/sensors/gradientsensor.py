from homeassistant.components.trend.binary_sensor import (
    SensorTrend
)
from custom_components.peaqhvac.const import DOMAIN
import custom_components.peaqhvac.extensionmethods as ex

class GradientSensor(SensorTrend):
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

        super().__init__(
            hass=hass,
            device_id=ex.nametoid(self._attr_name),
            friendly_name=self._attr_name,
            entity_id=listenerentity,
            attribute="",
            device_class=device_class,
            invert=False,
            max_samples=max_samples,
            min_gradient=min_gradient,
            sample_duration=sample_duration
        )

        self._hub = hub
        self._state = 0

    @property
    def icon(self) -> str:
        return "mdi:heat-wave"

    @property
    def unique_id(self):
        """Return a unique ID to use for this sensor."""
        return f"{DOMAIN}_{self._entry_id}_{ex.nametoid(self._attr_name)}"

    @property
    def device_info(self):
        """Return information to link this entity with the correct device."""
        return {"identifiers": {(DOMAIN, self._hub.hub_id)}}