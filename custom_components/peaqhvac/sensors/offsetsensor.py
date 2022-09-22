from custom_components.peaqhvac.sensors.sensorbase import SensorBase

class OffsetSensor(SensorBase):
    def __init__(self, hub, entry_id, name):
        self._sensorname = name
        self._attr_name = f"{hub.hubname} {name}"
        self._attr_unit_of_measurement = 'step'
        super().__init__(hub, self._attr_name, entry_id)
        self._state = 0
        self._offsets = {}
        self._offsets_tomorrow = {}

    @property
    def unit_of_measurement(self):
        return self._attr_unit_of_measurement

    @property
    def state(self) -> int:
        return self._state

    @property
    def icon(self) -> str:
        return "mdi:stairs"

    def update(self) -> None:
        self._state = self._hub.hvac.current_offset
        self._offsets = self._hub.hvac.current_offset_dict
        self._offsets_tomorrow = self._hub.hvac.current_offset_dict_tomorrow

    @property
    def extra_state_attributes(self) -> dict:
        attr_dict = {}

        attr_dict["Today"] = self._offsets
        attr_dict["Tomorrow"] = self._offsets_tomorrow
        return attr_dict
