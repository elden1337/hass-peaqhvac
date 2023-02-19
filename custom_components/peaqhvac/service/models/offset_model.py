from dataclasses import dataclass, field
import logging

_LOGGER = logging.getLogger(__name__)


@dataclass
class OffsetModel:
    peaks_today: list[int] = field(default_factory=lambda: [])
    calculated_offsets = {}, {}
    raw_offsets = {}, {}
    _tolerance = 0
    tolerance_raw = 0
    prognosis = None
    hub = None

    @property
    def tolerance(self) -> int:
        return self._tolerance

    @tolerance.setter
    def tolerance(self, val):
        old_tolerance = self._tolerance
        old_raw = self.tolerance_raw

        try:
            _val, temp = val
            self.tolerance_raw = _val
            self._tolerance = self.get_boundrary(
                adjustment=self.tolerance_raw,
                set_tolerance=self.get_tolerance_difference(temp)
            )
        except:
            self.tolerance_raw = val
            self._tolerance = val
        _LOGGER.debug(f"Tolerance has been updated. New tol is {self.tolerance} and raw is {self.tolerance_raw}")
        if any([old_raw != self.tolerance_raw]):
            self.hub.observer.broadcast("tolerance changed")

    @staticmethod
    def get_tolerance_difference(current_temp) -> int:
        """change the tolerance based on the current outside temperature"""
        if current_temp <= -10:
            return -2
        if current_temp <= -5:
            return -1
        if -5 < current_temp < 5:
            return 0
        if 5 <= current_temp < 10:
            return 1
        if 10 <= current_temp < 13:
            return 2
        if current_temp >= 13:
            return 3

    @staticmethod
    def get_boundrary(adjustment, set_tolerance) -> int:
        return max(0, min(10, set_tolerance + adjustment))
