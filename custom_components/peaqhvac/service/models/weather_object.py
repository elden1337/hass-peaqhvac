from dataclasses import dataclass, field
from datetime import datetime, timezone

from custom_components.peaqhvac.service.models.enums.weather_type import \
    WeatherType


@dataclass
class WeatherObject:
    _DTstr: str
    WeatherCondition: WeatherType
    Temperature: float
    Wind_Speed: float
    Wind_Bearing: float
    Precipitation_Probability: float
    Precipitation: float
    DT: datetime = field(init=False)

    def __post_init__(self):
        self.DT = self._parse_datetime()

    def _parse_datetime(self) -> datetime:
        time_obj = datetime.strptime(self._DTstr, "%Y-%m-%dT%H:%M:%S+00:00")
        utc_time = time_obj.replace(tzinfo=timezone.utc)
        return utc_time
