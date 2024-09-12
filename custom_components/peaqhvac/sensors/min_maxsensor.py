from homeassistant.components.sensor import SensorStateClass
from homeassistant.helpers.restore_state import RestoreEntity

from custom_components.peaqhvac.const import (
    AVERAGESENSOR_INDOORS,
    AVERAGESENSOR_OUTDOORS,
)
from custom_components.peaqhvac.sensors.sensorbase import SensorBase


class AverageSensor(SensorBase, RestoreEntity):
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, hub, entry_id, name):
        self._sensorname = name
        self._attr_name = f"{hub.hubname} {name}"
        self._attr_unit_of_measurement = "°C"
        super().__init__(hub, self._attr_name, entry_id)
        self._state = 0.0
        self._min = 0.0
        self._max = 0.0
        self._median = 0.0
        self._all_values = []

    @property
    def unit_of_measurement(self):
        return self._attr_unit_of_measurement

    @property
    def state(self) -> float:
        return round(float(self._state), 1)

    @property
    def icon(self) -> str:
        return "mdi:thermometer"

    def update(self) -> None:
        if not self._hub.is_initialized:
            return
        if self._sensorname == AVERAGESENSOR_INDOORS:
            self._state = self._hub.sensors.average_temp_indoors.value
            self._min = self._hub.sensors.average_temp_indoors.min
            self._max = self._hub.sensors.average_temp_indoors.max
            self._median = self._hub.sensors.average_temp_indoors.median
            self._all_values = self._hub.sensors.average_temp_indoors.all_values
        elif self._sensorname == AVERAGESENSOR_OUTDOORS:
            self._state = self._hub.sensors.average_temp_outdoors.value
            self._min = self._hub.sensors.average_temp_outdoors.min
            self._max = self._hub.sensors.average_temp_outdoors.max
            self._median = self._hub.sensors.average_temp_outdoors.median
            self._all_values = self._hub.sensors.average_temp_outdoors.all_values

    @property
    def extra_state_attributes(self) -> dict:
        attr_dict = {}

        attr_dict["max"] = float(self._max)
        attr_dict["min"] = float(self._min)
        attr_dict["median"] = float(self._median)
        attr_dict["values"] = list(self._all_values)

        return attr_dict

    async def async_added_to_hass(self):
        state = await super().async_get_last_state()
        if state:
            self._state = state.state
            _all_values = state.attributes.get("values", 50)
            if self._sensorname == AVERAGESENSOR_INDOORS:
                self._hub.sensors.average_temp_indoors.all_values = _all_values
            elif self._sensorname == AVERAGESENSOR_OUTDOORS:
                self._hub.sensors.average_temp_outdoors.all_values = _all_values
            self.update()
        else:
            self._state = 0.0
