import logging
from datetime import datetime
from functools import partial
from typing import Callable

from homeassistant.core import (
    HomeAssistant,
    callback,
    Event,
    EventStateChangedData,
)  # pylint: disable=E0401

from custom_components.peaqhvac.const import LATEST_WATER_BOOST, NEXT_WATER_START

from custom_components.peaqhvac.service.models.config_model import ConfigModel
from custom_components.peaqhvac.service.models.offsets_exportmodel import (
    OffsetsExportModel,
)
from custom_components.peaqhvac.service.observer.iobserver_coordinator import IObserver
from custom_components.peaqhvac.extensionmethods import async_iscoroutine

_LOGGER = logging.getLogger(__name__)


class Hub:
    hub_id = 1338
    hubname = "PeaqHvac"

    def __init__(
        self, hass: HomeAssistant, observer: IObserver, hub_options: ConfigModel
    ):
        self.trackerentities = []
        self._is_initialized = False
        self.state_machine = hass
        self.observer = observer
        self.options = hub_options
        self.sensors = None
        self.states = None
        self.hvac_service = None
        self.spotprice = None
        self.prognosis = None
        self.offset = None

    def price_below_min(self, hour: datetime) -> bool:
        try:
            return (
                self.spotprice.model.prices[hour.hour]
                <= self.sensors.peaqev_facade.min_price
            )
        except:
            _LOGGER.warning(
                f"Unable to get price for hour {hour}. min_price: {self.sensors.peaqev_facade.min_price}, num_prices_today: {len(self.spotprice.model.prices)}"
            )
            return False

    @property
    def is_initialized(self) -> bool:
        if self._is_initialized:
            return True
        return self._check_initialized()

    def _check_initialized(self) -> bool:
        if all([self.spotprice.is_initialized, self.prognosis.is_initialized]):
            self._is_initialized = True
            self.observer.activate()
            return True
        return False

    @callback
    async def async_on_change(self, event: Event[EventStateChangedData]) -> None:
        entity_id = event.data["entity_id"]
        old_state = event.data["old_state"]
        new_state = event.data["new_state"]
        if entity_id is not None:
            try:
                if old_state is None or old_state != new_state:
                    await self.states.async_update_sensor(entity_id, new_state.state)
            except Exception as e:
                _LOGGER.exception(
                    f"Unable to handle data: {entity_id} old: {old_state}, new: {new_state}. Raised expection: {e}"
                )

    async def call_enable_peaq(self):
        self.sensors.peaqhvac_enabled.value = True

    async def call_disable_peaq(self):
        self.sensors.peaqhvac_enabled.value = False

    async def call_set_mode(self, mode):
        # match towards enum. set hub to that state.
        pass

    async def async_get_internal_sensor(self, entity):
        lookup = {
            LATEST_WATER_BOOST: partial(
                getattr, self.hvac_service.water_heater, "latest_boost_call"
            ),
            NEXT_WATER_START: partial(
                getattr, self.hvac_service.water_heater, "next_water_heater_start"
            ),
        }

        func: Callable = lookup.get(entity, None)
        if await async_iscoroutine(func):
            return await func()
        else:
            return func()

    async def async_offset_export_model(self) -> OffsetsExportModel:
        ret = OffsetsExportModel(
            (self.offset.model.peaks_today, self.offset.model.peaks_tomorrow)
        )
        ret.raw_offsets = self.offset.model.raw_offsets
        ret.current_offset = self.offset.model.current_offset_dict
        ret.current_offset_tomorrow = self.offset.model.current_offset_dict_tomorrow

        return ret
