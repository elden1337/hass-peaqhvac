from homeassistant.helpers.restore_state import RestoreEntity

from custom_components.peaqhvac.const import (TRENDSENSOR_INDOORS,
                                              TRENDSENSOR_OUTDOORS)
from custom_components.peaqhvac.sensors.sensorbase import SensorBase


class TrendSensor(SensorBase, RestoreEntity):
    def __init__(self, hub, entry_id, name, icon):
        self._sensorname = name
        self._attr_name = f"{hub.hubname} {name}"
        self._icon = icon
        self._attr_unit_of_measurement = "°C/h"
        super().__init__(hub, self._attr_name, entry_id)
        self._state = 0
        self._samples = 0
        self._oldest_sample = "-"
        self._newest_sample = "-"
        self._samples_raw = []

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
        return attr_dict

    def update(self) -> None:
        if self._sensorname == TRENDSENSOR_INDOORS:
            self._state = self._hub.sensors.temp_trend_indoors.gradient
            self._samples = self._hub.sensors.temp_trend_indoors.samples
            self._oldest_sample = self._hub.sensors.temp_trend_indoors.oldest_sample
            self._newest_sample = self._hub.sensors.temp_trend_indoors.newest_sample
            self._samples_raw = self._hub.sensors.temp_trend_indoors.samples_raw
        elif self._sensorname == TRENDSENSOR_OUTDOORS:
            self._state = self._hub.sensors.temp_trend_outdoors.gradient
            self._samples = self._hub.sensors.temp_trend_outdoors.samples
            self._oldest_sample = self._hub.sensors.temp_trend_outdoors.oldest_sample
            self._newest_sample = self._hub.sensors.temp_trend_outdoors.newest_sample
            self._samples_raw = self._hub.sensors.temp_trend_outdoors.samples_raw

    async def async_added_to_hass(self):
        state = await super().async_get_last_state()
        if state:
            self._state = state.state
            self._samples = state.attributes.get("samples", 50)
            self._oldest_sample = state.attributes.get("oldest_sample", 50)
            self._newest_sample = state.attributes.get("newest_sample", 50)
            self._samples_raw = state.attributes.get("samples_raw", 50)
            if self._sensorname == TRENDSENSOR_INDOORS:
                self._hub.sensors.temp_trend_indoors.samples_raw = self._samples_raw
            elif self._sensorname == TRENDSENSOR_OUTDOORS:
                self._hub.sensors.temp_trend_outdoors.samples_raw = self._samples_raw
        else:
            self._state = 0
            self._samples = 0
            self._oldest_sample = "-"
            self._newest_sample = "-"
            self._samples_raw = []
