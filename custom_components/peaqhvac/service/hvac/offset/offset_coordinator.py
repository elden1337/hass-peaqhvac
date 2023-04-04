from __future__ import annotations

import logging
from typing import Tuple
from datetime import datetime
from custom_components.peaqhvac.service.hvac.offset.peakfinder import identify_peaks, smooth_transitions
from custom_components.peaqhvac.service.hvac.offset.offset_utils import offset_per_day, max_price_lower_internal
from peaqevcore.services.hourselection.hoursselection import Hoursselection
from custom_components.peaqhvac.service.models.offset_model import OffsetModel


_LOGGER = logging.getLogger(__name__)


class OffsetCoordinator:
    """The class that provides the offsets for the hvac"""

    def __init__(self, hub):
        self._hub = hub
        self.model = OffsetModel(hub)
        self.internal_preset = None
        self.hours = self._set_hours_type()
        self._prices = None
        self._prices_tomorrow = None
        self._hub.observer.add("prices changed", self._update_prices)
        self._hub.observer.add("prognosis changed", self._update_prognosis)
        self._hub.observer.add("hvac preset changed", self._update_preset)
        self._hub.observer.add("set temperature changed", self._set_offset)

    @property
    def prices(self) -> list:
        if not self._hub.sensors.peaqev_installed:
            return self.hours.prices
        return self._prices

    @property
    def prices_tomorrow(self) -> list:
        if not self._hub.sensors.peaqev_installed:
            return self.hours.prices_tomorrow
        return self._prices_tomorrow

    @property
    def offsets(self) -> dict:
        if not self._hub.sensors.peaqev_installed:
            return self.hours.offsets
        return self._hub.sensors.peaqev_facade.offsets

    def get_offset(self) -> Tuple[dict, dict]:
        """External entrypoint to the class"""
        if len(self.model.calculated_offsets[0]) == 0:
            _LOGGER.debug("no offsets available. recalculating")
            self._set_offset()
        return self.model.calculated_offsets

    def get_raw_offset(self) -> Tuple[dict, dict]:
        return self.model.raw_offsets

    def _update_prognosis(self) -> None:
        self.model.prognosis = self._hub.prognosis.prognosis
        self._set_offset()

    def _update_prices(self, prices):
        self._update_prices_internal(prices)
    
    def _update_preset(self) -> None:
        self.internal_preset = self._hub.sensors.set_temp_indoors.preset
        self._set_offset()

    def _update_prices_internal(self, prices) -> None:
        if not self._hub.sensors.peaqev_installed:
            self.hours.update_prices(prices[0], prices[1])
        else:
            if self._prices != prices[0]:
                self._prices = prices[0]
            if self._prices_tomorrow != prices[1]:
                self._prices_tomorrow = prices[1]
        self._set_offset()
        self._update_model()

    def max_price_lower(self, tempdiff: float) -> bool:
        """Temporarily lower to -10 if this hour is a peak for today and temp > set-temp + 0.5C"""
        return max_price_lower_internal(tempdiff, self.model.peaks_today)

    def _update_offset(self, weather_adjusted_today: dict | None = None) -> Tuple[dict, dict]:
        try:
            d = self.offsets
            if weather_adjusted_today is None:
                today = offset_per_day(
                    day_values=d.get('today'), 
                    tolerance=self.model.tolerance, 
                    indoors_preset=self._hub.sensors.set_temp_indoors.preset) 
            else:
                today = weather_adjusted_today.values()
            tomorrow = []
            if len(d.get('tomorrow', {})) > 0:
                tomorrow = offset_per_day(
                day_values=d.get('tomorrow'), 
                tolerance=self.model.tolerance, 
                indoors_preset=self._hub.sensors.set_temp_indoors.preset)
            return smooth_transitions(today=list(today), tomorrow=list(tomorrow), tolerance=self.model.tolerance)
        except Exception as e:
            _LOGGER.exception(f"Exception while trying to calculate offset: {e}")
            return {}, {}

    def _set_offset(self) -> None:
        if all([
            self.prices is not None,
            self.model.prognosis is not None
        ]):
            self.model.raw_offsets = self._update_offset()
            # if 23 <= len(self.prices) <= 25:
            #     self.model.raw_offsets = self._update_offset()
            # else:
            #     _LOGGER.debug(f"Prices are not ok. length is {len(self.prices)}. nordpool today len is {len(self._hub.nordpool.prices)}")
            try:
                _weather_dict = self._hub.prognosis.get_weatherprognosis_adjustment(self.model.raw_offsets)
                self.model.calculated_offsets = self._update_offset(_weather_dict[0])
            except Exception as e:
                _LOGGER.warning(f"Unable to calculate prognosis-offsets. Setting normal calculation: {e}")
                self.model.calculated_offsets = self.model.raw_offsets
            self._hub.observer.broadcast("offset recalculation")
        else:
            _LOGGER.debug("not possible to calculate offset.")

    def adjust_to_threshold(self, adjustment: int) -> int:
        ret = min(adjustment, self.model.tolerance) if adjustment >= 0 else max(adjustment, self.model.tolerance * -1)
        return int(round(ret, 0))

    def _update_model(self) -> None:
        self.model.peaks_today = identify_peaks(self.prices)
        self.model.peaks_tomorrow = identify_peaks(self.prices_tomorrow)


    def _set_hours_type(self):
        if not self._hub.sensors.peaqev_installed:
            _LOGGER.debug("initializing an hourselection-instance")
            return Hoursselection()
        _LOGGER.debug("found peaqev and will not init hourelection")
        return None