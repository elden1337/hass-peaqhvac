from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Tuple

import homeassistant.helpers.template as template

from custom_components.peaqhvac.service.models.prognosis_export_model import \
    PrognosisExportModel
from custom_components.peaqhvac.service.models.weather_object import \
    WeatherObject

_LOGGER = logging.getLogger(__name__)


class WeatherPrognosis:
    def __init__(self, hub):
        self._hub = hub
        self._hass = hub._hass
        self.prognosis_list: list[WeatherObject] = []
        self._hvac_prognosis_list: list = []
        self._current_temperature = 1000
        self.entity = ""
        self._is_initialized: bool = False
        self._setup_weather_prognosis()

    @property
    def is_initialized(self) -> bool:
        return self._is_initialized

    @property
    def prognosis(self) -> list:
        if len(self._hvac_prognosis_list) == 0:
            return self.get_hvac_prognosis(
                self._hub.sensors.average_temp_outdoors.value
            )
        return self._hvac_prognosis_list

    def _setup_weather_prognosis(self):
        try:
            entities = template.integration_entities(self._hass, "met")
            if len(entities) < 1:
                raise Exception("no entities found for weather.")
            _ent = [e for e in entities if e.endswith("_hourly")]
            if len(_ent) == 1:
                self.entity = _ent[0]
                self.update_weather_prognosis()
                self._is_initialized = True
            else:
                pass
        except Exception as e:
            msg = f"Peaqev was unable to get a single weather-entity. Disabling Weather-prognosis: {e}"
            _LOGGER.error(msg)

    def update_weather_prognosis(self):
        if self.is_initialized:
            ret = self._hass.states.get(self.entity)
            if ret is not None:
                try:
                    ret_attr = list(ret.attributes.get("forecast"))
                    if len(ret_attr) > 0:
                        self._set_prognosis(ret_attr)
                    else:
                        _LOGGER.error(
                            f"Wether prognosis cannot be updated :({len(ret_attr)})"
                        )
                except Exception:
                    # _LOGGER.exception(f"Could not parse today's prices from Nordpool. Unsolveable error. {e}")
                    return
            else:
                _LOGGER.error("could not get weather-prognosis.")
        else:
            _LOGGER.debug(
                "Tried to update weather-prognosis but the class is not initialized yet."
            )

    def get_hvac_prognosis(self, current_temperature: float) -> list:
        ret = []
        if not self.is_initialized:
            return ret
        try:
            self._current_temperature = float(current_temperature)
        except Exception as e:
            _LOGGER.debug(f"Could not parse temperature as float: {e}")
            return ret
        corrected_temp_delta = 0
        now = datetime.now()
        thishour = datetime(now.year, now.month, now.day, now.hour, 0, 0)

        valid_progs = [
            p for idx, p in enumerate(self.prognosis_list) if p.DT >= thishour
        ]
        if len(valid_progs) == 0:
            return ret
        for p in valid_progs:
            c = p.DT - thishour
            if c.seconds == 0:
                corrected_temp_delta = round(
                    self._current_temperature - p.Temperature, 2
                )
                continue
            if 3600 <= c.seconds <= 21600:
                # correct the temp
                temp = round(
                    p.Temperature + corrected_temp_delta / int(c.seconds / 3600), 1
                )
            else:
                temp = p.Temperature
            hourdiff = int(c.seconds / 3600)
            hour_prognosis = PrognosisExportModel(
                prognosis_temp=p.Temperature,
                corrected_temp=temp,
                windchill_temp=self._correct_temperature_for_windchill(
                    temp, p.Wind_Speed
                ),
                delta_temp_from_now=round(temp - self._current_temperature, 1),
                DT=p.DT,
                TimeDelta=hourdiff,
            )
            ret.append(hour_prognosis)

        self._hvac_prognosis_list = ret
        return ret

    def get_weatherprognosis_adjustment(self, offsets) -> Tuple[dict, dict]:
        self.update_weather_prognosis()
        ret = {}, offsets[1]
        for k, v in offsets[0].items():
            ret[0][k] = self._get_weatherprognosis_hourly_adjustment(k, v)
        return {k: v * -1 for (k, v) in ret[0].items()}, ret[1]

    def _get_weatherprognosis_hourly_adjustment(self, k, v):
        now = datetime.now()
        _next_prognosis = self._get_two_hour_prog(
            datetime(now.year, now.month, now.day, int(k), 0, 0)
        )
        if _next_prognosis is not None and int(k) >= now.hour:
            divisor = max((11 - _next_prognosis.TimeDelta) / 10, 0)
            adj = (
                int(round((_next_prognosis.delta_temp_from_now / 2.5) * divisor, 0))
                * -1
            )
            if adj != 0:
                if (v + adj) <= 0:
                    return (v + adj) * -1
                else:
                    return (v + adj) * -1
            else:
                return v * -1
        else:
            return v * -1

    def _set_prognosis(self, import_list: list):
        old_prognosis = self.prognosis_list
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
                    Precipitation=i["precipitation"],
                )
            )
        self.prognosis_list = ret
        if self.prognosis_list != old_prognosis:
            self._hub.observer.broadcast("prognosis changed")

    def _correct_temperature_for_windchill(
        self, temp: float, windspeed: float
    ) -> float:
        windspeed_corrected = windspeed
        ret = 13.12
        ret += 0.6215 * temp
        ret -= 11.37 * windspeed_corrected**0.16
        ret += 0.3965 * temp * windspeed_corrected**0.16
        return round(ret, 1)

    def _get_two_hour_prog(self, thishour: datetime) -> PrognosisExportModel | None:
        for p in self.prognosis:
            c = timedelta.total_seconds(p.DT - thishour)
            if c == 10800:
                return p
        return None
