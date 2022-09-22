
from custom_components.peaqhvac.sensors.sensorbase import SensorBase
from custom_components.peaqhvac.const import DOMAIN, TRENDSENSOR_INDOORS, TRENDSENSOR_OUTDOORS

class TrendSensor(SensorBase):
    def __init__(self, hub, entry_id, name):
        self._sensorname = name
        self._attr_name = f"{hub.hubname} {name}"
        self._attr_unit_of_measurement = '°C/h'
        super().__init__(hub, self._attr_name, entry_id)
        self._state = 0
        self._samples = 0
        self._oldest_sample = "-"
        self._newest_sample = "-"

    @property
    def unit_of_measurement(self):
        return self._attr_unit_of_measurement

    @property
    def state(self) -> float:
        fstate = float(self._state)
        return fstate if abs(fstate) < 10 else 0

    @property
    def icon(self) -> str:
        if self._sensorname == TRENDSENSOR_INDOORS:
            return "mdi:home-thermometer"
        return "mdi:sun-thermometer"

    @property
    def extra_state_attributes(self) -> dict:
        attr_dict = {}
        attr_dict["samples"] = self._samples
        attr_dict["oldest_sample"] = self._oldest_sample
        attr_dict["newest_sample"] = self._newest_sample
        return attr_dict

    def update(self) -> None:
        if self._sensorname == TRENDSENSOR_INDOORS:
            self._state = self._hub.sensors.temp_trend_indoors.gradient
            self._samples = self._hub.sensors.temp_trend_indoors.samples
            self._oldest_sample = self._hub.sensors.temp_trend_indoors.oldest_sample
            self._newest_sample = self._hub.sensors.temp_trend_indoors.newest_sample
        elif self._sensorname == TRENDSENSOR_OUTDOORS:
            self._state = self._hub.sensors.temp_trend_outdoors.gradient
            self._samples = self._hub.sensors.temp_trend_outdoors.samples
            self._oldest_sample = self._hub.sensors.temp_trend_outdoors.oldest_sample
            self._newest_sample = self._hub.sensors.temp_trend_outdoors.newest_sample