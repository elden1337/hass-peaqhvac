from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class PrognosisExportModel:
    prognosis_temp: float
    corrected_temp: float
    windchill_temp: float
    delta_temp_from_now: float = field(init=False)
    DT: datetime
    TimeDelta: int
    _base_temp: float = field(repr=False)

    def __post_init__(self):
        self.delta_temp_from_now=round(self.windchill_temp - self._base_temp, 1)