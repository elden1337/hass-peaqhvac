from dataclasses import dataclass, field

@dataclass
class OffsetModel:
    peaks_today: list[int] = field(default_factory=lambda: [])
    calculated_offsets = {}, {}
    raw_offsets = {}, {}
    _tolerance = 0
    tolerance_raw = 0
    prognosis = None

    @property
    def tolerance(self) -> int:
        return self._tolerance

    @tolerance.setter
    def tolerance(self, val):
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
        return max(-10, min(10, set_tolerance + adjustment))
