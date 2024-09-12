from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Tuple

import homeassistant.helpers.template as template
from peaqevcore.common.models.observer_types import ObserverTypes

from custom_components.peaqhvac.service.models.prognosis_export_model import (
    PrognosisExportModel,
)
from custom_components.peaqhvac.service.models.weather_object import WeatherObject

_LOGGER = logging.getLogger(__name__)


class WeatherPrognosis:
    def __init__(self, hass, average_temp_outdoors, observer):
        self._hass = hass
        self.average_temp_outdoors = average_temp_outdoors
        self.observer = observer
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
        if not self.is_initialized:
            return []
        self.update_weather_prognosis()
        if len(self._hvac_prognosis_list) == 0:
            try:
                return self.get_hvac_prognosis(self.average_temp_outdoors.value)
            except Exception as e:
                _LOGGER.warning(f"Could not get hvac-prognosis: {e}")
                return []
        return self._hvac_prognosis_list

    def update_weather_prognosis(self):
        if self.is_initialized:
            #     action: weather.get_forecasts
            #     target:
            #     entity_id: weather.hake
            # data:
            # type: hourly
            try:
                ret = self._hass.services.call(
                    "weather", "get_forecasts", {"type": "hourly"}
                )
            except Exception as e:
                _LOGGER.error(f"Could not get weather-prognosis: {e}")
                return
            # ret = self._hass.states.get(self.entity)
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
                    return
            else:
                _LOGGER.error("could not get weather-prognosis.")

    def get_weatherprognosis_adjustment(self, offsets: dict[datetime, int]) -> dict:
        self.update_weather_prognosis()
        ret = {
            k: v
            for k, v in offsets.items()
            if k.date == datetime.now().date() + timedelta(days=1)
        }
        rr = {
            k: self._get_weatherprognosis_hourly_adjustment(k.hour, v)
            for k, v in offsets.items()
            if k.date == datetime.now().date()
        }
        ret.update(rr)
        return ret
        # for hour, offset in offsets[0].items():
        #     ret[0][hour] = self._get_weatherprognosis_hourly_adjustment(hour, offset)
        # return {hour: offset for (hour, offset) in ret[0].items()}, ret[1]

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
        now = datetime.now().replace(minute=0, second=0, microsecond=0)

        valid_progs = [p for idx, p in enumerate(self.prognosis_list) if p.DT >= now]
        if len(valid_progs) == 0:
            return ret
        for p in valid_progs:
            c = p.DT - now
            if c.seconds == 0:
                corrected_temp_delta = round(
                    self._current_temperature - p.Temperature, 2
                )
                continue
            temp = self._get_temp(p, corrected_temp_delta, c)
            hourdiff = int(c.seconds / 3600)
            hour_prognosis = PrognosisExportModel(
                prognosis_temp=p.Temperature,
                corrected_temp=temp,
                windchill_temp=self._correct_temperature_for_windchill(
                    temp, p.Wind_Speed
                ),
                DT=p.DT,
                TimeDelta=hourdiff,
                _base_temp=self._current_temperature,
            )
            ret.append(hour_prognosis)

        self._hvac_prognosis_list = ret
        return ret

    def _get_temp(self, p, corrected_temp_delta, c):
        if 3600 <= c.seconds <= 14400:
            decay_factor = 1 / (c.seconds / 3600)
            corr = corrected_temp_delta * decay_factor
            t3 = p.Temperature + corr
            return round(t3, 1)
        return p.Temperature

    def _get_weatherprognosis_hourly_adjustment(self, hour, offset) -> int:
        now = datetime.now().replace(hour=hour, minute=0, second=0, microsecond=0)
        proghour = now
        if now.minute > 30:
            proghour = now + timedelta(hours=1)
        _next_prognosis = self._get_two_hour_prog(proghour)
        ret = offset
        if _next_prognosis is not None and int(hour) >= now.hour:
            divisor = max((11 - _next_prognosis.TimeDelta) / 10, 0)
            adjustment_divisor = 2.5 if _next_prognosis.windchill_temp > -2 else 2
            adj = (
                int(
                    round(
                        (_next_prognosis.delta_temp_from_now / adjustment_divisor)
                        * divisor,
                        0,
                    )
                )
                * -1
            )
            # if 14 < hour < 19:
            #    print(f"for {hour} the initial was {offset}, adjustment: {adj}, divisor:{divisor}, timedelta:{_next_prognosis.TimeDelta}, windchill:{_next_prognosis.windchill_temp}, deltatemp:{_next_prognosis.delta_temp_from_now}")
            ret = offset + adj
        return ret

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
            self.observer.broadcast(ObserverTypes.PrognosisChanged)

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

    def _setup_weather_prognosis(
        self,
    ):  # todo: this must be handled with weeather servicecall.
        self._is_initialized = True

        # try:
        #     entities = template.integration_entities(self._hass, "met")
        #     if len(entities) < 1:
        #         _LOGGER.warning("no entities found for weather. Cannot use weather prognosis")
        #     _ent = [e for e in entities]
        #     if len(_ent) >= 1:
        #         self.entity = _ent[0]
        #         self._is_initialized = True
        #         self.update_weather_prognosis()
        #         _LOGGER.debug("Weather prognosis is initialized")
        #         if len(_ent) > 1:
        #             _LOGGER.warning(
        #                 f"Peaqev found more than one weather-entity. Using the first one: {self.entity}"
        #             )
        #     else:
        #         pass
        # except Exception as e:
        #     msg = f"Peaqev was unable to get a single weather-entity. Disabling Weather-prognosis: {e}"
        #     _LOGGER.error(msg)
