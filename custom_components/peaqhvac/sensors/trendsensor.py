from datetime import datetime

from homeassistant.helpers.restore_state import RestoreEntity
from custom_components.peaqhvac.sensors.sensorbase import SensorBase


class TrendSensor(SensorBase, RestoreEntity):
    def __init__(self, hub, entry_id, name, icon, unit_of_measurement, sensor):
        self._sensorname = name
        self.datasensor = sensor
        self._attr_name = f"{hub.hubname} {name}"
        self._icon = icon
        self._attr_unit_of_measurement = unit_of_measurement
        super().__init__(hub, self._attr_name, entry_id)
        self._state = 0
        self._samples = 0
        self._oldest_sample = "-"
        self._newest_sample = "-"
        self._samples_raw = []
        self._latest_restart: datetime = None

    @property
    def unit_of_measurement(self):
        return self._attr_unit_of_measurement

    @property
    def state(self) -> float:
        fstate = float(self._state)
        return fstate if abs(fstate) < 5 else 0

    @property
    def icon(self) -> str:
        return self._icon

    @property
    def extra_state_attributes(self) -> dict:
        attr_dict = {}
        attr_dict["samples"] = self._samples
        attr_dict["oldest_sample"] = self._oldest_sample
        attr_dict["newest_sample"] = self._newest_sample
        attr_dict["samples_raw"] = self._samples_raw
        attr_dict["latest_restart"] = self._latest_restart
        return attr_dict

    async def async_update(self) -> None:

        self._state = getattr(self.datasensor, "trend")
        self._samples = getattr(self.datasensor, "samples")
        self._oldest_sample = getattr(self.datasensor, "oldest_sample")
        self._newest_sample = getattr(self.datasensor, "newest_sample")
        self._samples_raw = getattr(self.datasensor, "samples_raw")

    async def async_added_to_hass(self):
        self._latest_restart = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        state = await super().async_get_last_state()
        if state:
            self._state = state.state
            self._samples = state.attributes.get("samples", 50)
            self._oldest_sample = state.attributes.get("oldest_sample", 50)
            self._newest_sample = state.attributes.get("newest_sample", 50)
            self._samples_raw = state.attributes.get("samples_raw", 50)

            setattr(self.datasensor, "samples_raw", self._samples_raw)

        else:
            self._state = 0
            self._samples = 0
            self._oldest_sample = "-"
            self._newest_sample = "-"
            self._samples_raw = []
