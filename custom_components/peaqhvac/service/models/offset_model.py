import logging
from homeassistant.helpers.event import async_track_time_interval
from datetime import timedelta, datetime

from peaqevcore.common.models.observer_types import ObserverTypes

_LOGGER = logging.getLogger(__name__)


class OffsetModel:
    _peaks_today: list = []
    _peaks_tomorrow: list = []
    calculated_offsets = {}
    raw_offsets = {}
    _tolerance = None
    tolerance_raw = None
    prognosis = None
    _tolerance_difference: int = 0

    def __init__(self, hub):
        self.hub = hub
        async_track_time_interval(self.hub.state_machine, self.recalculate_tolerance, timedelta(seconds=120))
        self.hub.observer.add(ObserverTypes.HvacToleranceChanged, self.recalculate_tolerance)
        self.hub.observer.add(ObserverTypes.TemperatureOutdoorsChanged, self.recalculate_tolerance)

    @property
    def peaks_today(self) -> list:
        return self._peaks_today

    @peaks_today.setter
    def peaks_today(self, val: list):
        self._peaks_today = [v for v in val if 0 <= v < 24]

    @property
    def peaks_tomorrow(self) -> list:
        return self._peaks_tomorrow

    @peaks_tomorrow.setter
    def peaks_tomorrow(self, val: list):
        self._peaks_tomorrow = [v for v in val if 0 <= v < 24]

    @property
    def tolerance(self) -> int:
        if self._tolerance is None:
            self.recalculate_tolerance()
        return self._tolerance

    @tolerance.setter
    def tolerance(self, val):
        self._tolerance = val

    @property
    def current_offset_dict(self) -> dict:
        return {k: v for k, v in self.calculated_offsets.items() if k.date() == datetime.now().date()}

    @property
    def current_offset_dict_tomorrow(self) -> dict:
        return {k: v for k, v in self.calculated_offsets.items() if
                k.date() == datetime.now().date() + timedelta(days=1)}

    def recalculate_tolerance(self, *args):
        if self.hub.options.hvac_tolerance is not None:
            old_tolerance = self._tolerance
            old_raw = self.tolerance_raw
            self.tolerance_raw = self.hub.options.hvac_tolerance
            try:
                self._tolerance = self.get_boundrary(
                    adjustment=self.hub.options.hvac_tolerance,
                    set_tolerance=self.get_tolerance_difference(
                        self.hub.sensors.average_temp_outdoors.value
                    ),
                )
            except Exception as e:
                self._tolerance = self.hub.options.hvac_tolerance
                _LOGGER.warning(f"Error on recalculation of tolerance. Setting default. {e}")
            if any([old_raw != self.tolerance_raw, old_tolerance != self.tolerance]):
                _LOGGER.debug(
                    f"Tolerance has been updated. New tol is {self.tolerance} and raw is {self.tolerance_raw} for temp {self.hub.sensors.average_temp_outdoors.value}"
                )
                self.hub.observer.broadcast(ObserverTypes.OffsetRecalculation)

    def get_tolerance_difference(self, current_temp) -> int:
        """change the tolerance based on the current outside temperature"""
        match current_temp:
            case _ if current_temp <= -15:
                tolerance_difference = -2
            case _ if current_temp <= -7:
                tolerance_difference = -1
            case _:
                tolerance_difference = 0

        if tolerance_difference != self._tolerance_difference:
            self._tolerance_difference = tolerance_difference
            _LOGGER.debug(f"Lowering tolerance with {tolerance_difference} based on current temperature {current_temp}C.")
        return tolerance_difference

    @staticmethod
    def get_boundrary(adjustment, set_tolerance) -> int:
        return max(0, min(10, set_tolerance + adjustment))
