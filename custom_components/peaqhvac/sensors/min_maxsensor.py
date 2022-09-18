from custom_components.peaqhvac.const import AVERAGESENSOR_INDOORS, AVERAGESENSOR_OUTDOORS
from custom_components.peaqhvac.sensors.sensorbase import SensorBase
from homeassistant.helpers.restore_state import RestoreEntity

class AverageSensor(SensorBase, RestoreEntity):
    def __init__(
            self,
            hub,
            entry_id,
            name
    ):
        self._sensorname = name
        self._attr_name = f"{hub.hubname} {name}"
        self._attr_unit_of_measurement = '°C'
        super().__init__(hub, self._attr_name, entry_id)
        self._state = 0

    @property
    def unit_of_measurement(self):
        return self._attr_unit_of_measurement

    @property
    def state(self) -> float:
        return round(float(self._state),1)

    @property
    def icon(self) -> str:
        return "mdi:thermometer"

    def update(self) -> None:
        if self._sensorname == AVERAGESENSOR_INDOORS:
            self._state = self._hub.sensors.average_temp_indoors.value
        elif  self._sensorname == AVERAGESENSOR_OUTDOORS:
            self._state = self._hub.sensors.average_temp_outdoors.value

    async def async_added_to_hass(self):
        state = await super().async_get_last_state()
        if state:
            self._state = state.state
        else:
            self._state = 0