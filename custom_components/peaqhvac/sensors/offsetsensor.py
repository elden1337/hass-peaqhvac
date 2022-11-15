from custom_components.peaqhvac.sensors.sensorbase import SensorBase

class OffsetSensor(SensorBase):
    def __init__(self, hub, entry_id, name):
        self._sensorname = name
        self._attr_name = f"{hub.hubname} {name}"
        self._attr_unit_of_measurement = 'step'
        super().__init__(hub, self._attr_name, entry_id)
        self._state = None
        self._offsets = {}
        self._offsets_tomorrow = {}
        self._current_offset = None
        self._tempdiff_offset = None
        self._tempextremas_offset = None
        self._temptrend_offset = None

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
        self._current_offset = self._hub.hvac.house_heater.current_offset
        self._tempdiff_offset = self._hub.hvac.house_heater.current_tempdiff
        self._tempextremas_offset = self._hub.hvac.house_heater.current_temp_extremas
        self._temptrend_offset = self._hub.hvac.house_heater.current_temp_trend_offset


    @property
    def extra_state_attributes(self) -> dict:
        attr_dict = {}
        attr_dict["Current hour offset"] = self._current_offset
        attr_dict["Tempdiff offset"] = self._tempdiff_offset
        attr_dict["Temp extremas offset"] = self._tempextremas_offset
        attr_dict["Temp trend offset"] = self._temptrend_offset
        attr_dict["Today"] = self._offsets
        attr_dict["Tomorrow"] = self._offsets_tomorrow
        return attr_dict
