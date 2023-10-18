import logging
from datetime import datetime

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import async_track_state_change
from functools import partial
from typing import Callable

from custom_components.peaqhvac.const import LATEST_WATER_BOOST, NEXT_WATER_START
from custom_components.peaqhvac.service.hub.hubsensors import HubSensors
from custom_components.peaqhvac.service.hub.nordpool import NordPoolUpdater
from custom_components.peaqhvac.service.hub.state_changes import StateChanges
from custom_components.peaqhvac.service.hub.weather_prognosis import \
    WeatherPrognosis
from custom_components.peaqhvac.service.hvac.hvacfactory import HvacFactory
from custom_components.peaqhvac.service.hvac.offset.offset_coordinator import \
    OffsetCoordinator
from custom_components.peaqhvac.service.models.config_model import ConfigModel
from custom_components.peaqhvac.service.models.offsets_exportmodel import OffsetsExportModel
from custom_components.peaqhvac.service.observer.observer_service import Observer
from custom_components.peaqhvac.extensionmethods import async_iscoroutine
_LOGGER = logging.getLogger(__name__)


class Hub:
    hub_id = 1338
    hubname = "PeaqHvac"

    def __init__(self, hass: HomeAssistant, hub_options: ConfigModel):
        self._is_initialized = False
        self.hass = hass
        self.observer = Observer(self)
        self.options = hub_options
        self.sensors = HubSensors(self, hub_options, self.hass, self.get_peaqev())
        self.states = StateChanges(self, self.hass)
        self.hvac = HvacFactory.create(self.hass, self.options, self)
        self.nordpool = NordPoolUpdater(self.hass, self)
        self.prognosis = WeatherPrognosis(self)
        self.offset = OffsetCoordinator(self)
        self.options.hub = self

    async def async_setup(self) -> None:
        await self.nordpool.async_setup()
        await self.async_setup_trackers()

    async def async_setup_trackers(self):
        self.trackerentities = []
        self.trackerentities.append(self.nordpool.nordpool_entity)
        self.trackerentities.extend(self.options.indoor_tempsensors)
        self.trackerentities.extend(self.options.outdoor_tempsensors)
        await self.states.async_initialize_values()
        async_track_state_change(
            self.hass, self.trackerentities, self.async_state_changed
        )

    def price_below_min(self, hour:datetime) -> bool:
        try:
            return self.nordpool.prices[hour.hour] <= self.sensors.peaqev_facade.min_price
        except:
            _LOGGER.warning(f"Unable to get price for hour {hour}. min_price: {self.sensors.peaqev_facade.min_price}, num_prices_today: {len(self.nordpool.prices)}")
            return False

    @property
    def is_initialized(self) -> bool:
        if self._is_initialized:
            return True
        return self._check_initialized()

    def _check_initialized(self) -> bool:
        if all([self.nordpool.is_initialized, self.prognosis.is_initialized]):
            self._is_initialized = True
            self.observer.activate()
            return True
        return False

    @callback
    async def async_state_changed(self, entity_id, old_state, new_state):
        if entity_id is not None:
            try:
                if old_state is None or old_state != new_state:
                    await self.states.async_update_sensor(entity_id, new_state.state)
            except Exception as e:
                _LOGGER.exception(
                    f"Unable to handle data: {entity_id} old: {old_state}, new: {new_state}. Raised expection: {e}"
                )

    def get_peaqev(self):
        try:
            ret = self.hass.states.get("sensor.peaqev_threshold")
            if ret is not None:
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
        self.sensors.peaq_enabled.value = True

    async def call_disable_peaq(self):
        self.sensors.peaq_enabled.value = False

    async def call_set_mode(self, mode):
        # match towards enum. set hub to that state.
        pass

    @property
    def predicted_temp(self) -> float:
        return (
            self.sensors.average_temp_indoors.value
            + self.sensors.temp_trend_indoors.gradient
        )


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
        ret.raw_offsets = self.offset.model.raw_offsets[0]
        ret.current_offset = self.hvac.model.current_offset_dict
        ret.current_offset_tomorrow = self.hvac.model.current_offset_dict_tomorrow
        return ret

