from __future__ import annotations

import logging
from datetime import datetime
from typing import Tuple

from peaqevcore.common.models.observer_types import ObserverTypes
from peaqevcore.services.hourselection.hoursselection import Hoursselection

from custom_components.peaqhvac.service.hvac.house_heater.models.calculated_offset import CalculatedOffsetModel
from custom_components.peaqhvac.service.hvac.offset.models.offsets_model import OffsetsModel
from custom_components.peaqhvac.service.hvac.offset.offset_utils import (
    max_price_lower_internal, offset_per_day)
from custom_components.peaqhvac.service.hvac.offset.peakfinder import (
    identify_peaks, smooth_transitions)
from custom_components.peaqhvac.service.models.offset_model import OffsetModel

_LOGGER = logging.getLogger(__name__)


class OffsetCoordinator:
    """The class that provides the offsets for the hvac"""

    def __init__(self, hub):
        self._hub = hub
        self.model = OffsetModel(hub)
        self.hours = self._set_hours_type()
        self._prices = None
        self._prices_tomorrow = None
        self._hub.observer.add(ObserverTypes.PricesChanged, self._update_prices)
        self._hub.observer.add(ObserverTypes.SpotpriceInitialized, self._update_prices)
        self._hub.observer.add("prognosis changed", self._update_prognosis)
        self._hub.observer.add("hvac preset changed", self._set_offset)
        self._hub.observer.add("set temperature changed", self._set_offset)
        self._hub.observer.add("hvac tolerance changed", self._set_offset)

    @property #todo: move to hub
    def prices(self) -> list:
        if not self._hub.sensors.peaqev_installed:
            return self.hours.prices
        return self._prices

    @property #todo: move to hub
    def prices_tomorrow(self) -> list:
        if not self._hub.sensors.peaqev_installed:
            return self.hours.prices_tomorrow
        return self._prices_tomorrow

    @property
    def offsets(self) -> dict:
        if not self._hub.sensors.peaqev_installed:
            ret = self.hours.offsets
        else:
            ret = self._hub.sensors.peaqev_facade.offsets
            if len(ret) == 0 or not ret:
                _LOGGER.warning("Tried to get offsets from peaqev, but got nothing")
        return ret


    @property
    def current_offset(self) -> int:
        offsets = self.get_offset()
        return offsets.raw_offsets[0].get(datetime.now().hour, 0)

    def get_offset(self) -> OffsetsModel:
        """External entrypoint to the class"""
        self._set_offset()
        return OffsetsModel(
            self.model.calculated_offsets,
            self.model.raw_offsets
        )

    def _update_prognosis(self) -> None:
        self.model.prognosis = self._hub.prognosis.prognosis
        self._set_offset()

    def _update_prices(self, prices) -> None:
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
            _LOGGER.debug(f"updating offsets with {d}")
            today_values = d.get("today", {})
            tomorrow_values = d.get("tomorrow", {})
            today = self._calculate_offset_per_day(today_values, weather_adjusted_today)
            tomorrow = self._calculate_offset_per_day(tomorrow_values)
            return smooth_transitions(
                today=today,
                tomorrow=tomorrow,
                tolerance=self.model.tolerance,
            )
        except Exception as e:
            _LOGGER.exception(f"Exception while trying to calculate offset: {e}")
            return {}, {}

    def _calculate_offset_per_day(self, day_values: dict, weather_adjusted_today: dict | None = None) -> list:
        if weather_adjusted_today is None:
            indoors_preset = self._hub.sensors.set_temp_indoors.preset
            return offset_per_day(
                day_values=day_values,
                tolerance=self.model.tolerance,
                indoors_preset=indoors_preset,
            )
        else:
            return list(weather_adjusted_today.values())

    def _set_offset(self) -> None:
        if all([self.prices is not None, self.model.prognosis is not None]):
            self.model.raw_offsets = self._update_offset()
            try:
                _weather_dict = self._hub.prognosis.get_weatherprognosis_adjustment(
                    self.model.raw_offsets, self._hub.sensors.peaqev_facade.min_price
                )
                self.model.calculated_offsets = self._update_offset(_weather_dict[0])
            except Exception as e:
                _LOGGER.warning(
                    f"Unable to calculate prognosis-offsets. Setting normal calculation: {e}"
                )
                self.model.calculated_offsets = self.model.raw_offsets
        else:
            #_LOGGER.warning("not possible to calculate offset.")
            pass
        self._hub.observer.broadcast("offset recalculation")

    def adjust_to_threshold(self, offsetdata: CalculatedOffsetModel) -> int:
        adjustment = offsetdata.sum_values()
        if adjustment is None or self._hub.sensors.average_temp_outdoors.value > 13:
            return 0
        if self.model.tolerance is None:
            tolerance = 3
        else:
            tolerance = self.model.tolerance
        ret = (
            min(adjustment, tolerance)
            if adjustment >= 0
            else max(adjustment, tolerance * -1)
        )
        return int(round(ret, 0))

    def _update_model(self) -> None:
        self.model.peaks_today = identify_peaks(self.prices)
        self.model.peaks_tomorrow = identify_peaks(self.prices_tomorrow)

    def _set_hours_type(self):
        if not self._hub.sensors.peaqev_installed:
            _LOGGER.debug("initializing an hourselection-instance")
            return Hoursselection()
        _LOGGER.debug("found peaqev and will not init hourselection")
        return None
