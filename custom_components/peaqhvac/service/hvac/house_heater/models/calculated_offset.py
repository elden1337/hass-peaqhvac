from dataclasses import dataclass
import logging

_LOGGER = logging.getLogger(__name__)


@dataclass
class CalculatedOffsetModel:
    current_offset: int
    current_tempdiff: float
    current_temp_extremas: float
    current_temp_trend_offset: float

    def sum_values(self, extra_current: int = None) -> float:
        current = extra_current if extra_current is not None else self.current_offset
        ret = sum(
            [
                current,
                self.current_tempdiff,
                self.current_temp_extremas,
                self.current_temp_trend_offset,
            ]
        )
        return ret
