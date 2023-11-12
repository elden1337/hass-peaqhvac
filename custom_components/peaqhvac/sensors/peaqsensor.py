from datetime import datetime, timedelta

from homeassistant.helpers.restore_state import RestoreEntity

from custom_components.peaqhvac.const import HEATINGDEMAND, WATERDEMAND
from custom_components.peaqhvac.sensors.sensorbase import SensorBase


class PeaqSensor(SensorBase, RestoreEntity):
    def __init__(self, hub, entry_id, name: str, icon: str = "mdi:thermometer"):
        self._sensorname = name
        self._icon = icon
        self._attr_name = f"{hub.hubname} {name}"
        super().__init__(hub, self._attr_name, entry_id)
        self._state = ""

        if self._sensorname == WATERDEMAND:
            self._watertemp_trend = 0
            self._current_water_temperature = 0
            self._heat_water = False
            self._water_is_heating = False

    @property
    def state(self) -> str:
        return self._state

    @property
    def extra_state_attributes(self) -> dict:
        attr_dict = {}

        if self._sensorname == WATERDEMAND:
            attr_dict["watertemp_trend °/h"] = self._watertemp_trend
            attr_dict["current_temperature"] = self._current_water_temperature
            attr_dict["heat_water"] = self._heat_water
            attr_dict["water_is_heating"] = self._water_is_heating
        return attr_dict

    @property
    def icon(self) -> str:
        return self._icon

    async def async_update(self) -> None:
        if self._sensorname == HEATINGDEMAND:
            self._state = self._hub.hvac.house_heater.demand.value
        elif self._sensorname == WATERDEMAND:
            self._state = self._hub.hvac.water_heater.demand.value
            self._watertemp_trend = self._hub.hvac.water_heater.temperature_trend
            self._current_water_temperature = self._hub.hvac.hvac_watertemp
            self._heat_water = self._hub.hvac.water_heater.model.water_boost.value
            self._water_is_heating = self._hub.hvac.water_heater.water_heating

    async def async_added_to_hass(self):
        state = await super().async_get_last_state()
        if state:
            self._state = state.state
        else:
            self._state = ""
