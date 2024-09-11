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


_LOGGER = logging.getLogger(__name__)


class OffsetCoordinator:
    """The class that provides the offsets for the hvac"""
    def __init__(self, hub, observer: IObserver, hours_type: Hoursselection = None): #type: ignore
        self._hub = hub
        self.observer = observer
        self.model = OffsetModel(hub)
        self.hours = hours_type
        self.latest_raw_offset_update_hour: int = -1
        self.observer.add(ObserverTypes.PrognosisChanged, self._update_prognosis)
        self.observer.add(ObserverTypes.HvacPresetChanged, self._set_offset)
        self.observer.add(ObserverTypes.SetTemperatureChanged, self._set_offset)
        self.observer.add(ObserverTypes.HvacToleranceChanged, self._set_offset)

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
    def current_offset(self) -> int:
        ret = 0
        try:
            self._set_offset()
            if len(self.model.raw_offsets):
                ret = self.model.raw_offsets.get(datetime.now().replace(minute=0, second=0, microsecond=0), 0)
        except KeyError as e:
            _LOGGER.error(f"Unable to get current offset: {e}. raw_offsets: {self.model.raw_offsets}")
        finally:
            return ret

    #self.model.current_offset_dict_combined = ret.calculated_offsets

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
        cached_today = cache.get_cache_for_today(datetime.now().date(), self.prices)
        cached_tomorrow = cache.get_cache_for_today((datetime.now() + timedelta(days=1)).date(), self.prices_tomorrow)
        cached_midnight_problem = cache.get_cache_for_today(datetime.now().date() - timedelta(days=1), self.prices)

        #todo: re-add caching
        try:
            # if all([cached_today, cached_tomorrow]):
            #     #_LOGGER.debug("Using cached values for today and tomorrow")
            #     today_values = cached_today.offsets
            #     tomorrow_values = cached_tomorrow.offsets
            # elif cached_today:
            #     #_LOGGER.debug("Using cached values for today")
            #     existing_data = {datetime.now().date(): cached_today.offsets}
            #     d = set_offset_dict(self.prices+self.prices_tomorrow, datetime.now(), self.min_price, existing_data)
            #     today_values = d.get(datetime.now().date(), {})
            #     tomorrow_values = d.get((datetime.now() + timedelta(days=1)).date(), {})
            #     cache.update_cache((datetime.now() + timedelta(days=1)).date(), self.prices_tomorrow, tomorrow_values)
            # elif cached_midnight_problem:
            #     """interim fix til we have dates on all price-lists"""
            #     #_LOGGER.debug("Midnight issue occurred")
            #     today_values = cached_midnight_problem.offsets
            #     tomorrow_values = {}
            # else:
            #     #_LOGGER.debug("no cached values found")
            #     d = set_offset_dict(self.prices + self.prices_tomorrow, datetime.now(), self.min_price, {})
            #     today_values = d.get(datetime.now().date(), {})
            #     tomorrow_values = d.get((datetime.now() + timedelta(days=1)).date(), {})
            #     cache.update_cache(datetime.now().date(), self.prices, today_values)
            #     cache.update_cache((datetime.now() + timedelta(days=1)).date(), self.prices_tomorrow, tomorrow_values)

            all_values = set_offset_dict(self.prices+self.prices_tomorrow, datetime.now(), self.min_price)
            _LOGGER.debug("all_values", all_values, self.prices, self.prices_tomorrow, self.min_price)
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
            else:
                _LOGGER.debug("No prognosis available", self._hub.prognosis.prognosis)
            self.observer.broadcast(ObserverTypes.OffsetRecalculation)
        else:
            if self._hub.is_initialized:
                _LOGGER.warning(f"Hub is ready but I'm unable to set offset. Prices num:{len(self.prices) if self.prices else 0}")

    def _update_model(self) -> None:
        self.model.peaks_today = identify_peaks(self.prices)
        self.model.peaks_tomorrow = identify_peaks(self.prices_tomorrow)







