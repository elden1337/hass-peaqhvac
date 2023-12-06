import logging
import time
from datetime import datetime, timedelta

from peaqevcore.common.models.observer_types import ObserverTypes
from peaqevcore.common.trend import Gradient

from custom_components.peaqhvac.service.hvac.const import DEFAULT_WATER_BOOST
from custom_components.peaqhvac.service.hvac.interfaces.iheater import IHeater
from peaqevcore.common.wait_timer import WaitTimer
from custom_components.peaqhvac.service.hvac.water_heater.const import *
from custom_components.peaqhvac.service.hvac.water_heater.water_heater_next_start import NextWaterBoost, get_demand, \
    DEMAND_MINUTES
from custom_components.peaqhvac.service.models.enums.demand import Demand
from custom_components.peaqhvac.service.models.enums.hvac_presets import \
    HvacPresets
from homeassistant.helpers.event import async_track_time_interval
from custom_components.peaqhvac.service.hvac.water_heater.models.waterbooster_model import \
    WaterBoosterModel

_LOGGER = logging.getLogger(__name__)

"""
we shouldnt need two booleans to tell if we are heating or trying to heat.
make the signaling less complicated, just calculate the need and check whether heating is already happening.
"""

class WaterHeater(IHeater):
    def __init__(self, hvac, hub):
        self._hub = hub
        super().__init__(hvac=hvac)
        self._current_temp = None
        self._wait_timer = WaitTimer(timeout=WAITTIMER_TIMEOUT, init_now=False)
        self._wait_timer_peak = WaitTimer(timeout=WAITTIMER_TIMEOUT, init_now=False)
        self.temp_trend = Gradient(
            max_age=3600, max_samples=5, precision=2, ignore=0, outlier=20
        )
        self.model = WaterBoosterModel(self._hub.state_machine)
        self.booster = NextWaterBoost(
            min_price = self._hub.sensors.peaqev_facade.min_price,
            non_hours = self._hub.options.heating_options.non_hours_water_boost,
            demand_hours = self._hub.options.heating_options.demand_hours_water_boost
        )

        self._hub.observer.add(ObserverTypes.OffsetsChanged, self._update_operation)
        self._hub.observer.add("water boost done", self.async_reset_water_boost)
        async_track_time_interval(
            self._hub.state_machine, self.async_update_operation, timedelta(seconds=30)
        )

    @property
    def is_initialized(self) -> bool:
        return self._current_temp is not None

    @property
    def temperature_trend(self) -> float:
        """returns the current temp_trend in C/hour"""
        return self.temp_trend.trend

    @property
    def latest_boost_call(self) -> str:
        """For Lovelace-purposes. Converts and returns epoch-timer to readable datetime-string"""
        if self.model.latest_boost_call > 0:
            return time.strftime("%Y-%m-%d %H:%M", time.localtime(self.model.latest_boost_call))
        return "-"

    def import_latest_boost_call(self, strtime):
        struct_time = time.strptime(strtime, "%Y-%m-%d %H:%M")
        new = time.mktime(struct_time)
        current = self.model.latest_boost_call
        self.model.latest_boost_call = max(new,current)

    @property
    def current_temperature(self) -> float:
        """The current reported water-temperature in the hvac"""
        return self._current_temp

    @current_temperature.setter
    def current_temperature(self, val):
        floatval = float(val)
        try:
            self._check_and_add_trend_reading(floatval)
            if self._current_temp != floatval:
                self._current_temp = floatval
                old_demand = self.demand.value
                self.demand = self._current_temp
                if self.demand.value != old_demand:
                    _LOGGER.debug(f"Water temp changed to {val} which caused demand to change from {old_demand} to {self.demand.value}")
                self._hub.observer.broadcast(ObserverTypes.WatertempChange)
                self._update_operation()
        except ValueError as E:
            _LOGGER.warning(f"unable to set {val} as watertemperature. {E}")
            self.model.water_boost.value = False

    def _check_and_add_trend_reading(self, val):
        raw = self.temp_trend.samples_raw
        if len(raw) > 0:
            last = raw[0]
            if last[1] != val or time.time() - last[0] > 300:
                self.temp_trend.add_reading(val=val, t=time.time())
            else:
                return
        self.temp_trend.add_reading(val=val, t=time.time())

    @property
    def demand(self) -> Demand:
        return self._demand

    @demand.setter
    def demand(self, temp):
        self._demand = self._get_demand()

    def _get_demand(self):
        ret = get_demand(self.current_temperature)
        return ret

    @property
    def water_heating(self) -> bool:
        """Return true if the water is currently being heated"""
        return self.temperature_trend > 4 or self.model.water_boost.value

    @property
    def next_water_heater_start(self) -> datetime:
        next_start = self.model.next_water_heater_start
        if next_start < datetime.now()+timedelta(minutes=10):
            self.model.bus_fire_once("peaqhvac.upcoming_water_heater_warning", {"new": True}, next_start)
        return next_start

    def _get_next_start(self, target_temp: int) -> tuple[datetime, int|None]:
        if self.water_heating:
            """no need to calculate if we are already heating or trying to heat"""
            self.model.next_water_heater_start = datetime.max
            return self.model.next_water_heater_start, None
        preset = self._hub.sensors.set_temp_indoors.preset
        ret, override_demand = self.booster.next_predicted_demand(
            prices_today=self._hub.spotprice.model.prices,
            prices_tomorrow=self._hub.spotprice.model.prices_tomorrow,
            preset=preset,
            temp=self.current_temperature,
            temp_trend=self.temp_trend.gradient_raw,
            target_temp=target_temp,
            latest_boost=datetime.fromtimestamp(self.model.latest_boost_call),
        )
        ret = min(ret, datetime.fromtimestamp(self.model.latest_boost_call) + timedelta(hours=24))
        if ret < datetime.now() +timedelta(days=-3):
            ret = datetime.max
            override_demand = None
        self.model.next_water_heater_start = ret
        return ret, override_demand

    async def async_reset_water_boost(self):
        self.model.water_boost.value = False
        await self.async_update_operation()

    async def async_update_operation(self, caller=None):
        self._update_operation()

    def _check_and_reset_boost(self) -> None:
        if self.model.water_boost.value and self.model.latest_boost_call - time.time() > 3600:
            _LOGGER.debug("Water boost has been on for more than an hour. Turning off.")
            self.model.water_boost.value = False
            
    def _update_operation(self) -> None:
        self._check_and_reset_boost()
        if self.is_initialized:
            if self._hub.sensors.set_temp_indoors.preset != HvacPresets.Away:
                self._set_water_heater_operation(HIGHTEMP_THRESHOLD)
            elif self._hub.sensors.set_temp_indoors.preset == HvacPresets.Away:
                self._set_water_heater_operation(LOWTEMP_THRESHOLD)

    def _set_water_heater_operation(self, target_temp: int) -> None:
        next_start, override_demand = self._get_next_start(target_temp)
        #_LOGGER.debug(f"Next water heater start is {next_start}. Override demand is {override_demand}")
        try:
            self.__set_toggle_boost_next_start(next_start, override_demand)
        except Exception as e:
            _LOGGER.error(
                f"Could not check water-state: {e}")

    def __set_toggle_boost_next_start(self, next_start: datetime, override_demand: int = None) -> None:
        try:
            if next_start <= datetime.now() and not self.model.water_boost.value:
                preset = self._hub.sensors.set_temp_indoors.preset
                if override_demand is not None:
                    demand_minutes = override_demand
                else:
                    demand_minutes = DEMAND_MINUTES[preset].get(self._get_demand(), DEFAULT_WATER_BOOST)

                if demand_minutes > 0:
                    self.model.water_boost.value = True
                    self.model.latest_boost_call = time.time()
                    _LOGGER.debug("Next water heater start is now. Turning on water heating.")
                    self._hub.observer.broadcast("water boost start", demand_minutes*60)
                elif override_demand is not None and demand_minutes == 0:
                    _LOGGER.error("Should not be able to get here.")
        except Exception as e:
            _LOGGER.warning(f"Could not set water boost: {e}")

    def __is_below_start_threshold(self) -> bool:
        return all([
            datetime.now().minute >= 30,
            self._hub.sensors.peaqev_facade.below_start_threshold])

    def __is_price_below_min_price(self) -> bool:
        return float(self._hub.spotprice.state) <= float(self._hub.sensors.peaqev_facade.min_price)




