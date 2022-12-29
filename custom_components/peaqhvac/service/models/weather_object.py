from dataclasses import field, dataclass
from datetime import datetime
from time import strptime, mktime

from custom_components.peaqhvac.service.models.enums.weather_type import WeatherType


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
        time_obj = strptime(self._DTstr, "%Y-%m-%dT%H:%M:%S+00:00")
        return datetime.fromtimestamp(mktime(time_obj))
