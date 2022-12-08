from datetime import datetime
import logging

import homeassistant.helpers.template as template
from enum import Enum
from dataclasses import dataclass, field
from time import mktime, strptime

_LOGGER = logging.getLogger(__name__)


class WeatherType(Enum):
    Sunny = "sunny"
    Cloudy = "cloudy"
    PartlyCloudy = "partlycloudy"
    Snowy = "snowy"


@dataclass
class PrognosisExportModel:
    prognosis_temp: float
    corrected_temp: float
    windchill_temp: float
    delta_temp_from_now: float
    DT: datetime
    TimeDelta: int


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


class WeatherPrognosis:
    def __init__(self, hub):
        self._hub = hub
        self._hass = hub._hass
        self.prognosis_list: list[WeatherObject] = []
        self._hvac_prognosis_list: list = []
        self._current_temperature = 1000
        self.entity = ""
        self.initialized: bool = False
        self._setup_weather_prognosis()

    @property
    def prognosis(self) -> list:
        _LOGGER.debug(self._hvac_prognosis_list)
        if len(self._hvac_prognosis_list) == 0:
            return self.get_hvac_prognosis(self._hub.sensors.average_temp_outdoors.value)
        return self._hvac_prognosis_list

    def _setup_weather_prognosis(self):
        try:
            entities = template.integration_entities(self._hass, 'met')
            if len(entities) < 1:
                raise Exception("no entities found for weather.")
            _ent = [e for e in entities if e.endswith("_hourly")]
            if len(_ent) == 1:
                self.entity = _ent[0]
                self.update_weather_prognosis()
                self.initialized = True
            else:
                pass
        except Exception as e:
            msg = f"Peaqev was unable to get a single weather-entity. Disabling Weather-prognosis: {e}"
            _LOGGER.error(msg)

    def update_weather_prognosis(self):
        if self.initialized:
            ret = self._hass.states.get(self.entity)
            if ret is not None:
                try:
                    ret_attr = list(ret.attributes.get("forecast"))
                    if len(ret_attr) > 0:
                        self._set_prognosis(ret_attr)
                    else:
                        _LOGGER.error(f"Wether prognosis cannot be updated :({len(ret_attr)})")
                        pass
                except Exception as e:
                    #_LOGGER.exception(f"Could not parse today's prices from Nordpool. Unsolveable error. {e}")
                    pass
                    return
            else:
                _LOGGER.error("could not get weather-prognosis.")
        else:
            _LOGGER.debug("Tried to update weather-prognosis but the class is not initialized yet.")

    def get_hvac_prognosis(self, current_temperature: float):
        # if current_temperature == self._current_temperature:
        #     return
        try:
            self._current_temperature = float(current_temperature)
        except Exception as e:
            _LOGGER.debug(f"Could not parse temperature as float: {e}")
            return
        ret = []
        if not self.initialized:
            return
        corrected_temp_delta = 0
        now = datetime.now()
        thishour = datetime(now.year, now.month, now.day, now.hour, 0, 0)

        valid_progs = [p for idx, p in enumerate(self.prognosis_list) if p.DT >= thishour]
        if len(valid_progs) == 0:
            _LOGGER.debug("No prognosis available")
            return
        for p in valid_progs:
            c = p.DT - thishour
            if c.seconds == 0:
                corrected_temp_delta = round(self._current_temperature - p.Temperature, 2)
                continue
            if 3600 <= c.seconds <= 21600:
                # correct the temp
                temp = round(p.Temperature + corrected_temp_delta / int(c.seconds / 3600), 1)
            else:
                temp = p.Temperature
            hourdiff = int(c.seconds / 3600)
            hour_prognosis = PrognosisExportModel(
                prognosis_temp=p.Temperature,
                corrected_temp=temp,
                windchill_temp=self._correct_temperature_for_windchill(temp, p.Wind_Speed),
                delta_temp_from_now=round(temp - self._current_temperature, 1),
                DT=p.DT,
                TimeDelta=hourdiff
            )
            ret.append(hour_prognosis)

        self._hvac_prognosis_list = ret
        return ret

    def _set_prognosis(self, import_list: list):
        ret = []
        for i in import_list:
            ret.append(
                WeatherObject(
                    _DTstr=i["datetime"],
                    WeatherCondition=i["condition"],
                    Temperature=i["temperature"],
                    Wind_Speed=i["wind_speed"],
                    Wind_Bearing=i["wind_bearing"],
                    Precipitation_Probability=i["precipitation_probability"],
                    Precipitation=i["precipitation"])
            )
        self.prognosis_list = ret

    def _correct_temperature_for_windchill(self, temp: float, windspeed: float) -> float:
        windspeed_corrected = windspeed
        ret = 13.12 + (0.6215 * temp) - (11.37 * windspeed_corrected ** 0.16) + (
                    0.3965 * temp * windspeed_corrected ** 0.16)
        return round(ret, 1)

#
#
# w = WeatherPrognosis()
# w.set_prognosis(test_input)
#
# for ww in w.prognosis_list:
#     print(ww)
#
# prog = w.get_hvac_prognosis(1.6)
#
# for p in prog:
#     print(p)
#
#







