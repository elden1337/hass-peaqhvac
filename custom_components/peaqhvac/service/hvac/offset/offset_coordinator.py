from __future__ import annotations

import logging
from abc import abstractmethod
from datetime import datetime, timedelta
from typing import Tuple

from peaqevcore.common.models.observer_types import ObserverTypes
from peaqevcore.services.hourselection.hoursselection import Hoursselection

from custom_components.peaqhvac.service.hvac.house_heater.models.calculated_offset import CalculatedOffsetModel
from custom_components.peaqhvac.service.hvac.offset.models.offsets_model import OffsetsModel
from custom_components.peaqhvac.service.hvac.offset.offset_utils import (
    max_price_lower_internal, offset_per_day, set_offset_dict)
from custom_components.peaqhvac.service.hvac.offset.peakfinder import (
    identify_peaks, smooth_transitions)
from custom_components.peaqhvac.service.models.offset_model import OffsetModel

_LOGGER = logging.getLogger(__name__)


class OffsetCoordinator:
    """The class that provides the offsets for the hvac"""

    def __init__(self, hub, hours_type: Hoursselection = None): #type: ignore
        self._hub = hub
        self.model = OffsetModel(hub)
        self.hours = hours_type

        self._hub.observer.add(ObserverTypes.PricesChanged, self.async_update_prices)
        self._hub.observer.add(ObserverTypes.SpotpriceInitialized, self.async_update_prices)
        self._hub.observer.add(ObserverTypes.PrognosisChanged, self._update_prognosis)
        self._hub.observer.add(ObserverTypes.HvacPresetChanged, self._set_offset)
        self._hub.observer.add(ObserverTypes.SetTemperatureChanged, self._set_offset)
        self._hub.observer.add(ObserverTypes.HvacToleranceChanged, self._set_offset)

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

    @abstractmethod
    async def async_update_prices(self, prices) -> None:
        pass

    def max_price_lower(self, tempdiff: float) -> bool:
        return max_price_lower_internal(tempdiff, self.model.peaks_today)

    def _update_offset(self, weather_adjusted_today: dict | None = None) -> Tuple[dict, dict]:
        try:
            d = set_offset_dict(self.prices+self.prices_tomorrow, datetime.now(), self.min_price, self.model.base_offsets)
            today_values = d.get(datetime.now().date(), {})
            tomorrow_values = d.get((datetime.now() + timedelta(days=1)).date(), {})
            today = self._calculate_offset_per_day(today_values, weather_adjusted_today)
            tomorrow = self._calculate_offset_per_day(tomorrow_values)
            self.model.base_offsets = d
            return smooth_transitions(#67
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
        if self.prices is not None:
            self.model.raw_offsets = self._update_offset()
            self.model.calculated_offsets = self.model.raw_offsets

            if self.model.prognosis is not None:
                try:
                    _weather_dict = self._hub.prognosis.get_weatherprognosis_adjustment(self.model.raw_offsets)
                    if len(_weather_dict[0]) > 0:
                        self.model.calculated_offsets = self._update_offset(_weather_dict[0])
                except Exception as e:
                    _LOGGER.warning(
                        f"Unable to calculate prognosis-offsets. Setting normal calculation: {e}"
                    )
            self._hub.observer.broadcast(ObserverTypes.OffsetRecalculation)
        else:
            _LOGGER.warning("Unable to set offset. Prices are not properly. state:{self.prices}")

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







