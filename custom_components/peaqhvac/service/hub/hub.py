import logging
from datetime import datetime

from homeassistant.core import HomeAssistant, callback, Event, EventStateChangedData
from homeassistant.helpers.event import async_track_state_change_event
from functools import partial
from typing import Callable

from custom_components.peaqhvac.const import LATEST_WATER_BOOST, NEXT_WATER_START
from custom_components.peaqhvac.service.hub.hubsensors import HubSensors
from custom_components.peaqhvac.service.hub.state_changes import StateChanges
from custom_components.peaqhvac.service.hub.weather_prognosis import \
    WeatherPrognosis
from custom_components.peaqhvac.service.hvac.hvacfactory import HvacFactory
from custom_components.peaqhvac.service.hvac.offset.offset_coordinator_factory import OffsetFactory
from custom_components.peaqhvac.service.hvac.update_system import UpdateSystem
from custom_components.peaqhvac.service.models.config_model import ConfigModel
from custom_components.peaqhvac.service.models.offsets_exportmodel import OffsetsExportModel
from custom_components.peaqhvac.service.observer.observer_coordinator import Observer
from custom_components.peaqhvac.extensionmethods import async_iscoroutine
import sys
if 'pytest' not in sys.modules:
    from peaqevcore.common.spotprice.spotprice_factory import SpotPriceFactory
    from peaqevcore.common.models.peaq_system import PeaqSystem

_LOGGER = logging.getLogger(__name__)


class Hub:
    hub_id = 1338
    hubname = "PeaqHvac"

    def __init__(self, hass: HomeAssistant, hub_options: ConfigModel):
        self._is_initialized = False
        self.state_machine = hass
        self.observer = Observer(self) #todo: move to creation factory
        self.options = hub_options
        self.peaqev_discovered: bool = self.get_peaqev()
        self.sensors = HubSensors(self, hub_options, hass, self.peaqev_discovered)
        self.states = StateChanges(self, hass)
        self.hvac = HvacFactory.create(hass, self.options, self, self.observer)
        self.update_system = UpdateSystem(hass, self, self.observer, self.hvac.set_operation_call_parameters)
        self.spotprice = SpotPriceFactory.create(
            hub=self,
            observer=self.observer,
            system=PeaqSystem.PeaqHvac,
            test=False,
            is_active=True
        )

        self.prognosis = WeatherPrognosis(hass, self.sensors.average_temp_outdoors, self.observer)
        self.offset = OffsetFactory.create(self, observer=self.observer)
        self.options.hub = self

    async def async_setup(self) -> None:
        await self.async_setup_trackers()

    async def async_setup_trackers(self):
        self.trackerentities = []
        self.trackerentities.append(self.spotprice.entity)
        self.trackerentities.extend(self.options.indoor_tempsensors)
        self.trackerentities.extend(self.options.outdoor_tempsensors)
        await self.states.async_initialize_values()
        async_track_state_change_event(
            self.state_machine, self.trackerentities, self._async_on_change
        )

    def price_below_min(self, hour:datetime) -> bool:
        try:
            return self.spotprice.model.prices[hour.hour] <= self.sensors.peaqev_facade.min_price
        except:
            _LOGGER.warning(f"Unable to get price for hour {hour}. min_price: {self.sensors.peaqev_facade.min_price}, num_prices_today: {len(self.spotprice.model.prices)}")
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
    async def _async_on_change(self, event: Event[EventStateChangedData]) -> None:
        entity_id = event.data["entity_id"]
        old_state = event.data["old_state"]
        new_state = event.data["new_state"]
        if entity_id is not None:
            try:
                if old_state is None or old_state != new_state:
                    await self.states.async_update_sensor(entity_id, new_state.state)
            except Exception as e:
                _LOGGER.exception(f"Unable to handle data: {entity_id} old: {old_state}, new: {new_state}. Raised expection: {e}")

    def get_peaqev(self):
        try:
            ret = self.state_machine.states.get("sensor.peaqev_threshold")
            if ret is not None:
                if ret.state:
                    _LOGGER.debug(
                        "Discovered Peaqev-entities, will adhere to peak-shaving."
                    )
                    return True
            _LOGGER.debug(
                "Unable to discover Peaqev-entities, will not adhere to peak-shaving."
            )
            return False
        except:
            _LOGGER.debug(
                "Unable to discover Peaqev-entities, will not adhere to peak-shaving."
            )
            return False

    async def call_enable_peaq(self):
        self.sensors.peaqhvac_enabled.value = True

    async def call_disable_peaq(self):
        self.sensors.peaqhvac_enabled.value = False

    async def call_set_mode(self, mode):
        # match towards enum. set hub to that state.
        pass


    async def async_get_internal_sensor(self, entity):
        lookup = {
        LATEST_WATER_BOOST: partial(getattr, self.hvac.water_heater, "latest_boost_call"),
        NEXT_WATER_START: partial(getattr, self.hvac.water_heater, "next_water_heater_start")
        }

        func: Callable = lookup.get(entity, None)
        if await async_iscoroutine(func):
            return await func()
        else:
            return func()

    async def async_offset_export_model(self) -> OffsetsExportModel:
        ret = OffsetsExportModel(
        (self.offset.model.peaks_today, self.offset.model.peaks_tomorrow))
        ret.raw_offsets = self.offset.model.raw_offsets
        ret.current_offset = self.offset.model.current_offset_dict
        ret.current_offset_tomorrow = self.offset.model.current_offset_dict_tomorrow

        return ret

