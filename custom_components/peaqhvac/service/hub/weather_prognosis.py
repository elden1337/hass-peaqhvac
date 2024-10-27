from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Tuple

import homeassistant.helpers.template as template
from homeassistant.helpers.event import async_track_time_interval
from peaqevcore.common.models.observer_types import ObserverTypes

from custom_components.peaqhvac.service.models.prognosis_export_model import \
    PrognosisExportModel
from custom_components.peaqhvac.service.models.weather_object import \
    WeatherObject

_LOGGER = logging.getLogger(__name__)


class WeatherPrognosis:
    def __init__(self, hass, average_temp_outdoors, observer, weather_entity: str):
        self._hass = hass
        self.average_temp_outdoors = average_temp_outdoors
        self.observer = observer
        self.prognosis_list: list[WeatherObject] = []
        self._hvac_prognosis_list: list = []
        self._weather_export_model: list = []
        self._current_temperature = 1000
        self.entity = weather_entity
        _LOGGER.debug("WeatherPrognosis initialized with entity: %s", self.entity)
        if self.entity is not None:
            async_track_time_interval(self._hass, self.async_update_weather, timedelta(seconds=30))

    @property
    def prognosis(self) -> list:
        return self._weather_export_model

    async def async_update_weather(self, *args):
        await self.update_weather_prognosis()
        if len(self._hvac_prognosis_list) > 0:
            ret = self._hvac_prognosis_list
        else:
            try:
                ret = self.get_hvac_prognosis(
                    self.average_temp_outdoors.value
                )
            except Exception as e:
                _LOGGER.warning(f"Could not get hvac-prognosis: {e}")
                ret = []
        if ret != self._weather_export_model:
            self.observer.broadcast(ObserverTypes.PrognosisChanged)
            self._weather_export_model = ret

    async def update_weather_prognosis(self):
        try:
            ret = await self._hass.services.async_call(
                "weather",
                "get_forecasts",
                {"type": "hourly", "entity_id": self.entity},
                blocking=True,
                return_response=True
            )
        except Exception as e:
            _LOGGER.error(f"Could not get weather-prognosis: {e}")
            return
        if ret is not None:
            try:
                ret_attr = ret.get(self.entity, {}).get("forecast", [])
                if len(ret_attr):
                    self._set_prognosis(ret_attr)
                else:
                    _LOGGER.error(
                        f"Wether prognosis cannot be updated :({len(ret_attr)})"
                    )
            except Exception as e:
                _LOGGER.error(f"Could not update weather-prognosis: {e}")
                return
        else:
            _LOGGER.error("could not get weather-prognosis.")

    def get_weatherprognosis_adjustment(self, offsets:dict[datetime, int]) -> dict:
        ret = {k:v for k,v in offsets.items() if k.date == datetime.now().date()+timedelta(days=1)}
        rr = {k:self._get_weatherprognosis_hourly_adjustment(k.hour, v) for k,v in offsets.items() if k.date == datetime.now().date()}
        ret.update(rr)
        return ret

    def get_hvac_prognosis(self, current_temperature: float) -> list:
        ret = []
        try:
            self._current_temperature = float(current_temperature)
        except Exception as e:
            _LOGGER.warning(f"Could not parse temperature as float: {e}")
            return ret
        corrected_temp_delta = 0
        now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)

        valid_progs = [
            p for idx, p in enumerate(self.prognosis_list) if p.DT >= now
        ]
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
                windchill_temp=self._correct_temperature_for_windchill(temp, p.Wind_Speed),
                DT=p.DT,
                TimeDelta=hourdiff,
                _base_temp = self._current_temperature
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
        try:
            now = datetime.now().replace(hour=hour, minute=0, second=0, microsecond=0)
            proghour = now
            if now.minute > 30:
                proghour = now + timedelta(hours=1)
            proghour = proghour.astimezone(timezone.utc)
            _next_prognosis = self._get_two_hour_prog(proghour)
            ret = offset
            if _next_prognosis is not None and int(hour) >= now.hour:
                divisor = max((11 - _next_prognosis.TimeDelta) / 10, 0)
                adjustment_divisor = 2.5 if _next_prognosis.windchill_temp > -2 else 2
                adj = (int(round((_next_prognosis.delta_temp_from_now / adjustment_divisor) * divisor, 0)) * -1)
                ret = offset + adj
            return ret
        except Exception as e:
            _LOGGER.error(f"Could not get weatherprognosis adjustment: {e}")
            return offset

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
                    Precipitation=i["precipitation"],
                )
            )
        if ret != self.prognosis_list:
            self.prognosis_list = ret
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
