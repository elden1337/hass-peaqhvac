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
        self._temp_trend = Gradient(
            max_age=3600, max_samples=10, precision=1, ignore=0
        )
        self.model = WaterBoosterModel(self._hub.state_machine)
        self.booster = NextWaterBoost()
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
        return self._temp_trend.gradient

    @property
    def latest_boost_call(self) -> str:
        """For Lovelace-purposes. Converts and returns epoch-timer to readable datetime-string"""
        if self.model.latest_boost_call > 0:
            return time.strftime("%Y-%m-%d %H:%M", time.localtime(self.model.latest_boost_call))
        return "-"

    def import_latest_boost_call(self, strtime):
        struct_time = time.strptime(strtime, "%Y-%m-%d %H:%M")
        self.model.latest_boost_call = time.mktime(struct_time)

    @property
    def current_temperature(self) -> float:
        """The current reported water-temperature in the hvac"""
        return self._current_temp

    @current_temperature.setter
    def current_temperature(self, val):
        try:
            self._temp_trend.add_reading(val=float(val), t=time.time())
            if self._current_temp != float(val):
                self._current_temp = float(val)
                old_demand = self.demand.value
                self.demand = self._current_temp
                if self.demand.value != old_demand:
                    _LOGGER.debug(f"Water temp changed to {val} which caused demand to change from {old_demand} to {self.demand.value}")
                self._hub.observer.broadcast(ObserverTypes.WatertempChange)
                self._update_operation()
        except ValueError as E:
            _LOGGER.warning(f"unable to set {val} as watertemperature. {E}")
            self.model.water_boost.value = False

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
        return self.temperature_trend > 0 or self.model.water_boost.value

    @property
    def next_water_heater_start(self) -> datetime:
        next_start = self.model.next_water_heater_start
        if next_start < datetime.now()+timedelta(minutes=10):
            self.model.bus_fire_once("peaqhvac.upcoming_water_heater_warning", {"new": True}, next_start)
        return next_start

    def _get_next_start(self, target_temp: int) -> datetime:
        if self.water_heating:
            """no need to calculate if we are already heating or trying to heat"""
            self.model.next_water_heater_start = datetime.max
            return self.model.next_water_heater_start
        demand = self._get_demand()
        preset = self._hub.sensors.set_temp_indoors.preset
        ret = self.booster.next_predicted_demand(
            prices_today=self._hub.spotprice.model.prices,
            prices_tomorrow=self._hub.spotprice.model.prices_tomorrow,
            min_price=self._hub.sensors.peaqev_facade.min_price,
            demand=DEMAND_MINUTES[preset][demand],
            preset=preset,
            temp=self.current_temperature,
            temp_trend=self._temp_trend.gradient_raw,
            target_temp=target_temp,
            non_hours=self._hub.options.heating_options.non_hours_water_boost
        )
        if ret != self.model.next_water_heater_start:
            _LOGGER.debug(f"Next water heater start changed from {self.model.next_water_heater_start} to {ret}.")
            self.model.next_water_heater_start = ret
        return ret

    async def async_reset_water_boost(self):
        self.model.water_boost.value = False
        await self.async_update_operation()

    async def async_update_operation(self, caller=None):
        self._update_operation()

    def _update_operation(self) -> None:
        if self.is_initialized:
            if self._hub.sensors.set_temp_indoors.preset != HvacPresets.Away:
                self._set_water_heater_operation(HIGHTEMP_THRESHOLD)
            elif self._hub.sensors.set_temp_indoors.preset == HvacPresets.Away:
                self._set_water_heater_operation(LOWTEMP_THRESHOLD)

    def _set_water_heater_operation(self, target_temp: int) -> None:
        ee = None
        next_start = self._get_next_start(target_temp)
        try:
            if not self.model.water_boost.value:
                self.__set_toggle_boost_next_start(next_start)
        except Exception as e:
            _LOGGER.error(
                f"Could not check water-state: {e} with extended {ee}")

    def __set_toggle_boost_next_start(self, next_start) -> None:
        try:
            if next_start <= datetime.now():
                _LOGGER.debug("Next water heater start is now. Turning on water heating.")
                self.model.water_boost.value = True
                self.model.latest_boost_call = time.time()
                demand = self._get_demand()
                preset = self._hub.sensors.set_temp_indoors.preset
                demand_minutes = DEMAND_MINUTES[preset].get(demand, DEFAULT_WATER_BOOST)
                self._hub.observer.broadcast("water boost start", demand_minutes)
        except Exception as e:
            pass

    def __is_below_start_threshold(self) -> bool:
        return all([
            datetime.now().minute >= 30,
            self._hub.sensors.peaqev_facade.below_start_threshold])

    def __is_price_below_min_price(self) -> bool:
        return float(self._hub.spotprice.state) <= float(self._hub.sensors.peaqev_facade.min_price)




