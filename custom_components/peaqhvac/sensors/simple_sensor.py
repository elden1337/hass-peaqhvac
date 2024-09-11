from datetime import datetime, timedelta

from homeassistant.helpers.restore_state import RestoreEntity

from custom_components.peaqhvac.const import (
    HEATINGDEMAND,
    WATERDEMAND,
    NEXT_WATER_START,
    LATEST_WATER_BOOST,
)
from custom_components.peaqhvac.sensors.sensorbase import SensorBase
import logging

_LOGGER = logging.getLogger(__name__)


class PeaqSimpleSensor(SensorBase, RestoreEntity):
    def __init__(
        self,
        hub,
        entry_id,
        name: str,
        internal_entity: str,
        icon: str = "mdi:clock-end",
    ):
        self._sensorname = name
        self._icon = icon
        self._attr_name = f"{hub.hubname} {name.capitalize()}"
        super().__init__(hub, self._attr_name, entry_id)
        self._internal_entity = internal_entity
        self._state = ""

    @property
    def state(self) -> str:
        return self._state

    @property
    def icon(self) -> str:
        return self._icon

    async def async_update(self) -> None:
        ret = await self._hub.async_get_internal_sensor(self._internal_entity)
        if ret is not None:
            if self._internal_entity == NEXT_WATER_START:
                self._state = self._set_next_start(ret)
            else:
                self._state = ret

    @staticmethod
    def _set_next_start(next_start: datetime) -> str:
        if next_start > datetime.now() + timedelta(days=2):
            return "-"
        return next_start.strftime("%Y-%m-%d %H:%M")

    async def async_added_to_hass(self):
        state = await super().async_get_last_state()
        if state:
            self._state = state.state
            if self._internal_entity == LATEST_WATER_BOOST:
                self._hub.hvac_service.water_heater.import_latest_boost_call(
                    self._state
                )
                self._hub.hvac_service.water_heater.is_initialized = True
        else:
            self._state = "-"
            if self._internal_entity == LATEST_WATER_BOOST:
                self._hub.hvac_service.water_heater.is_initialized = True
