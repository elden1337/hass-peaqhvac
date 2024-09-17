from __future__ import annotations

import logging
from abc import abstractmethod
from datetime import datetime, timedelta
from peaqevcore.common.models.observer_types import ObserverTypes
from peaqevcore.services.hourselection.hoursselection import Hoursselection
import custom_components.peaqhvac.service.hvac.offset.offset_cache as cache
from custom_components.peaqhvac.service.hvac.offset.offset_utils import (
    max_price_lower_internal, offset_per_day, set_offset_dict)
from custom_components.peaqhvac.service.hvac.offset.peakfinder import (
    identify_peaks, smooth_transitions)
from custom_components.peaqhvac.service.models.offset_model import OffsetModel
from custom_components.peaqhvac.service.observer.iobserver_coordinator import IObserver
from homeassistant.helpers.event import async_track_time_interval


_LOGGER = logging.getLogger(__name__)


class OffsetCoordinator:
    """The class that provides the offsets for the hvac"""
    def __init__(self, hub, observer: IObserver, hours_type: Hoursselection = None): #type: ignore
        self._hub = hub
        self.observer = observer
        self.model = OffsetModel(hub)
        self.hours = hours_type
        self._current_raw_offset: int|None = None #move from here?
        self.latest_raw_offset_update_hour: int = -1
        self.observer.add(ObserverTypes.PrognosisChanged, self._update_prognosis)
        self.observer.add(ObserverTypes.HvacPresetChanged, self._set_offset)
        self.observer.add(ObserverTypes.SetTemperatureChanged, self._set_offset)
        self.observer.add("ObserverTypes.OffsetPreRecalculation", self._set_offset)
        async_track_time_interval(
            self._hub.state_machine, self._create_current_raw_offset, timedelta(minutes=1)
        )
        self._create_current_raw_offset()

    @property
    @abstractmethod
    def prices(self) -> list:
        pass

    @property
    @abstractmethod
    def prices_tomorrow(self) -> list:
        pass

    @property
    @abstractmethod
    def min_price(self) -> float:
        pass

    @property
    def current_offset(self) -> int|None:
        return self._current_raw_offset

    def _create_current_raw_offset(self, *args) -> None:
        ret = 0
        initialized = False
        try:
            if len(self.model.raw_offsets):
                latest_key = max((key for key in self.model.raw_offsets if key <= datetime.now()), default=None)
                if latest_key is not None:
                    ret = self.model.raw_offsets[latest_key]
                    initialized = True
        except KeyError as e:
            _LOGGER.error(
                f"Unable to get current offset: {e}. raw_offsets: {self.model.raw_offsets}"
            )
        finally:
            if self._current_raw_offset is not None or initialized:
                if self._current_raw_offset != ret:
                    self._current_raw_offset = ret
                    _LOGGER.debug(f"current_raw_offset updated to {self._current_raw_offset}")
                    self._set_offset()

    def _update_prognosis(self) -> None:
        self.model.prognosis = self._hub.prognosis.prognosis
        _LOGGER.debug("prognosis updated to", self.model.prognosis)
        self._set_offset()

    @abstractmethod
    async def async_update_prices(self, prices) -> None:
        pass

    def max_price_lower(self, tempdiff: float) -> bool:
        return max_price_lower_internal(tempdiff, self.model.peaks_today)

    def _update_offset(self, weather_adjusted_today: dict | None = None) -> dict:
        try:
            all_values = set_offset_dict(self.prices+self.prices_tomorrow, datetime.now(), self.min_price,{})
            #_LOGGER.debug(f"all_values: {all_values}")
            offsets_per_day = self._calculate_offset_per_day(all_values, weather_adjusted_today)
            tolerance = self.model.tolerance if self.model.tolerance is not None else 3
            for k, v in offsets_per_day.items():
                if v > tolerance:
                    offsets_per_day[k] = tolerance
                elif v < -self.model.tolerance:
                    offsets_per_day[k] = -tolerance

            return smooth_transitions(
                vals=offsets_per_day,
                tolerance=self.model.tolerance,
            )

        except Exception as e:
            _LOGGER.exception(f"Exception while trying to calculate offset: {e}")
            return {}

    def _calculate_offset_per_day(self, day_values: dict, weather_adjusted_today: dict | None = None) -> dict:
        if weather_adjusted_today is None:
            indoors_preset = self._hub.sensors.set_temp_indoors.preset
            return offset_per_day(
                all_prices=self.prices+self.prices_tomorrow,
                day_values=day_values,
                tolerance=self.model.tolerance,
                indoors_preset=indoors_preset,
            )
        else:
            return weather_adjusted_today

    def _set_offset(self) -> None:
        if self.prices is not None:
            self.model.raw_offsets = self._update_offset()
            self.model.calculated_offsets = self.model.raw_offsets
            if len(self._hub.prognosis.prognosis) > 0:
                try:
                    _weather_dict = self._hub.prognosis.get_weatherprognosis_adjustment(self.model.raw_offsets)
                    _LOGGER.debug("weather-prognosis", _weather_dict)
                    if len(_weather_dict.items()) > 0:
                        _LOGGER.debug("weather-prognosis", _weather_dict)
                        self.model.calculated_offsets = self._update_offset(_weather_dict)
                except Exception as e:
                    _LOGGER.warning(
                        f"Unable to calculate prognosis-offsets. Setting normal calculation: {e}"
                    )
            if len(self.model.raw_offsets):
                if not self.current_offset:
                    self._create_current_raw_offset()
                if self.current_offset:
                    self.observer.broadcast(ObserverTypes.OffsetRecalculation, self.current_offset)
        else:
            if self._hub.is_initialized:
                _LOGGER.warning(f"Hub is ready but I'm unable to set offset. Prices num:{len(self.prices) if self.prices else 0}")

    def _update_model(self) -> None:
        self.model.peaks_today = identify_peaks(self.prices)
        self.model.peaks_tomorrow = identify_peaks(self.prices_tomorrow)
        self.model.raw_offsets = self._update_offset()







