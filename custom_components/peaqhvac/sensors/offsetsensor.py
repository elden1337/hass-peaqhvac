from custom_components.peaqhvac.sensors.sensorbase import SensorBase

class OffsetSensor(SensorBase):
    def __init__(self, hub, entry_id, name):
        self._sensorname = name
        self._attr_name = f"{hub.hubname} {name}"
        self._attr_unit_of_measurement = 'step'
        super().__init__(hub, self._attr_name, entry_id)
        self._state = 0

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
