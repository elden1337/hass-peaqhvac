from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Tuple

from peaqevcore.common.models.observer_types import ObserverTypes
from custom_components.peaqhvac.service.hvac.house_heater.house_heater_helpers import HouseHeaterHelpers
from custom_components.peaqhvac.service.hvac.house_heater.models.calculated_offset import CalculatedOffsetModel
from custom_components.peaqhvac.service.hvac.house_heater.models.offset_adjustments import OffsetAdjustments
from custom_components.peaqhvac.service.hvac.house_heater.temperature_helper import HouseHeaterTemperatureHelper
from custom_components.peaqhvac.service.hvac.interfaces.iheater import IHeater
from custom_components.peaqhvac.service.models.enums.demand import Demand

_LOGGER = logging.getLogger(__name__)

OFFSET_MIN_VALUE = -10


class HouseHeaterCoordinator(IHeater):
    def __init__(self, hvac):
        self._hvac = hvac
        self._degree_minutes = 0
        self._current_offset: int = 0
        self._offsets: dict = {}
        self._current_adjusted_offset: int = 0
        self._temp_helper = HouseHeaterTemperatureHelper(hub=hvac.hub)
        self._helpers = HouseHeaterHelpers(hvac=hvac)
        super().__init__(hvac=hvac)

    @property
    def aux_offset_adjustments(self) -> dict:
        return self._helpers._aux_offset_adjustments

    @property
    def current_adjusted_offset(self) -> int:
        return int(self._current_adjusted_offset)

    @current_adjusted_offset.setter
    def current_adjusted_offset(self, val) -> None:
        if isinstance(val, (float, int)):
            self._current_adjusted_offset = val

    @property
    def is_initialized(self) -> bool:
        return True

    @IHeater.demand.setter
    def demand(self, val):
        self._demand = val

    @property
    def current_offset(self) -> int:
        return self._current_offset

    @current_offset.setter
    def current_offset(self, val) -> None:
        if isinstance(val, (float, int)):
            self._current_offset = val

    @property
    def current_tempdiff(self):
        return self._temp_helper.get_tempdiff_inverted(self.current_offset)

    def get_current_offset(self) -> Tuple[int, bool]:
        self._offsets = self._hvac.model.current_offset_dict_combined
        _force_update: bool = False

        outdoor_temp = self._hvac.hub.sensors.average_temp_outdoors.value
        temp_diff = self._hvac.hub.sensors.get_tempdiff()
        stop_heating_temp = self._hvac.hub.options.heating_options.outdoor_temp_stop_heating
        if (outdoor_temp > stop_heating_temp or
            self._hvac.hub.offset.max_price_lower(temp_diff)) and outdoor_temp >= 0:
            self._helpers._aux_offset_adjustments[OffsetAdjustments.PeakHour] = OFFSET_MIN_VALUE
            return OFFSET_MIN_VALUE, True
        else:
            self._helpers._aux_offset_adjustments[OffsetAdjustments.PeakHour] = 0

        # Get the calculated offset data and update the current offset to keep the compressor running
        offsetdata = self.get_calculated_offsetdata(_force_update)
        self._helpers._keep_compressor_running(offsetdata)

        # If offset will be < 0 and temp is lower than set temp, do special lowering to safe money
        if offsetdata.sum_values() <= 0 and self.current_tempdiff <= 0:
            ret = self._helpers._get_lower_offset(offsetdata)
            self.current_adjusted_offset = ret
            return int(ret), _force_update

        # If the offset should be adjusted, adjust it, update the current adjusted offset,
        # and return it along with the update flag
        if self._helpers._should_adjust_offset(offsetdata):
            ret = self._hvac.hub.offset.adjust_to_threshold(offsetdata)
            self.current_adjusted_offset = ret
            return int(ret), _force_update

        # Temporarily lower the offset if necessary and update the update flag
        lowered_offset = self._helpers._temporarily_lower_offset(offsetdata)
        if lowered_offset < offsetdata.sum_values():
            offsetdata.current_offset = lowered_offset
            _force_update = True

        # If an update is needed, broadcast an update operation
        if _force_update:
            self._hvac.hub.observer.broadcast(ObserverTypes.UpdateOperation)

        # Adjust the offset to the threshold, update the current adjusted offset,
        # and return it along with the update flag
        ret = self._hvac.hub.offset.adjust_to_threshold(offsetdata)
        self.current_adjusted_offset = int(ret)
        return self.current_adjusted_offset, _force_update

    def _get_demand(self) -> Demand:
        return self._helpers._helper_get_demand()

    def get_calculated_offsetdata(self, _force_update: bool = False) -> CalculatedOffsetModel:
        self._check_next_hour_offset(force_update=_force_update)
        return CalculatedOffsetModel(self.current_offset,
                                     self._temp_helper.get_tempdiff_inverted(self.current_offset),
                                     self._temp_helper.get_temp_extremas(self.current_offset),
                                     self._temp_helper.get_temp_trend_offset())

    async def async_update_operation(self):
        pass

    def _check_next_hour_offset(self, force_update: bool) -> None:
        if not len(self._offsets):
            return
        hour = datetime.now().replace(minute=0, second=0, microsecond=0)
        if datetime.now().minute >= 40:
            hour += timedelta(hours=1)
        try:
            if self._hvac.hub.price_below_min(hour):
                _offset = max(self._offsets[hour],0)
            else:
                _offset = self._offsets[hour]
        except:
            _LOGGER.warning(
                "No Price-offsets have been calculated. Setting base-offset to 0."
            )
            _offset = 0
        if self.current_offset != _offset:
            force_update = True
            self.current_offset = _offset





