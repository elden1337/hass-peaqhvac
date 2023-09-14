import logging
import time
from datetime import datetime, timedelta

import custom_components.peaqhvac.extensionmethods as ex
from peaqevcore.common.trend import Gradient
from custom_components.peaqhvac.service.hvac.interfaces.iheater import IHeater
from peaqevcore.common.wait_timer import WaitTimer
from custom_components.peaqhvac.service.hvac.water_heater.const import *
from custom_components.peaqhvac.service.hvac.water_heater.water_heater_next_start import NextWaterBoost
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

DEMAND_MINUTES = {
    HvacPresets.Normal: {
        Demand.NoDemand:     0,
        Demand.LowDemand:    26,
        Demand.MediumDemand: 35,
        Demand.HighDemand:   45
    },
    HvacPresets.Eco: {
        Demand.NoDemand:     0,
        Demand.LowDemand:    26,
        Demand.MediumDemand: 35,
        Demand.HighDemand:   45
    },
    HvacPresets.Away: {
        Demand.NoDemand:     0,
        Demand.LowDemand:    0,
        Demand.MediumDemand: 26,
        Demand.HighDemand:   26
    }
}


class WaterHeater(IHeater):
    def __init__(self, hvac):
        self._hvac = hvac
        super().__init__(hvac=hvac)
        self._current_temp = None
        self._boost_non_hours: list[int] = [7, 11, 12, 15, 16, 17] #todo make this an option in the config
        self._wait_timer = WaitTimer(timeout=WAITTIMER_TIMEOUT, init_now=False)
        self._wait_timer_peak = WaitTimer(timeout=WAITTIMER_TIMEOUT, init_now=False)
        self._temp_trend = Gradient(
            max_age=3600, max_samples=10, precision=1, ignore=0
        )
        self.model = WaterBoosterModel(self._hvac.hub.hass)
        self.booster = NextWaterBoost()
        self._hvac.hub.observer.add("offsets changed", self._update_operation)
        async_track_time_interval(
            self._hvac.hub.hass, self.async_update_operation, timedelta(seconds=30)
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
                self._hvac.hub.observer.broadcast("watertemp change")
                self._update_operation()
        except ValueError as E:
            _LOGGER.warning(f"unable to set {val} as watertemperature. {E}")
            self.model.try_heat_water.value = False

    @property
    def demand(self) -> Demand:
        return self._get_demand()

    @IHeater.demand.setter
    def demand(self, val):
        self._demand = val

    @property
    def water_boost(self) -> bool:
        """Returns true if we should try and heat the water"""
        return self.model.try_heat_water.value
        #return any([self.model.next_water_heater_start <= datetime.now(), self.water_heating])

    @property
    def water_heating(self) -> bool:
        """Return true if the water is currently being heated"""
        return self.temperature_trend > 0 or self.model.pre_heating.value

    @property
    def next_water_heater_start(self) -> datetime:
        next_start = self._get_next_start()
        if next_start < datetime.now()+timedelta(minutes=10):
            self.model.bus_fire_once("peaqhvac.upcoming_water_heater_warning", {"new": True}, next_start)
        self.model.next_water_heater_start = next_start
        return next_start

    def _get_demand(self) -> Demand:
        temp = self.current_temperature
        if temp is None:
            return Demand.NoDemand
        if 0 < temp < 100:
            if temp >= 40:
                return Demand.NoDemand
            if temp > 35:
                return Demand.LowDemand
            if temp >= 25:
                return Demand.MediumDemand
            if temp < 25:
                return Demand.HighDemand
        return Demand.NoDemand

    def _get_next_start(self) -> datetime:

        if self.water_boost or self.model.pre_heating.value:
            """no need to calculate if we are already heating or trying to heat"""
            return datetime.max
        demand = self.demand
        preset = self._hvac.hub.sensors.set_temp_indoors.preset
        if demand is Demand.NoDemand:
            return self.booster.next_predicted_demand(
                prices_today=self._hvac.hub.nordpool.prices,
                prices_tomorrow=self._hvac.hub.nordpool.prices_tomorrow,
                min_demand=DEMAND_MINUTES[preset][Demand.LowDemand],
                temp=self.current_temperature,
                temp_trend=self._temp_trend.gradient_raw,
                target_temp=HIGHTEMP_THRESHOLD,
                non_hours=self._boost_non_hours
            )
        return self.booster.get_next_start(
            prices_today=self._hvac.hub.nordpool.prices,
            prices_tomorrow=self._hvac.hub.nordpool.prices_tomorrow,
            demand=DEMAND_MINUTES[preset][demand],
            non_hours=self._boost_non_hours
        )

    async def async_update_operation(self, caller=None):
        self._update_operation()

    def _update_operation(self) -> None:
        if self.is_initialized:
            if self._hvac.hub.sensors.set_temp_indoors.preset != HvacPresets.Away:
                self._set_water_heater_operation_home()
            elif self._hvac.hub.sensors.set_temp_indoors.preset == HvacPresets.Away:
                self._set_water_heater_operation_away()

    def _set_water_heater_operation_home(self) -> None:
        ee = None
        try:
            if self._hvac.hub.sensors.peaqev_installed:
                if all([self._hvac.hub.sensors.peaqev_facade.above_stop_threshold,self.model.try_heat_water.value, 10 <= datetime.now().minute < 55]):
                    _LOGGER.debug("Peak is being breached. Turning off water heating")
                    try:
                        self._set_boost(False)
                    except Exception as e:
                        ee = f"1: {e}"
                elif self._is_below_start_threshold():
                    try:
                        if self._get_next_start() <= datetime.now():
                            self.model.pre_heating.value = True
                            self._toggle_boost(timer_timeout=None)
                    except Exception as e:
                        ee = f"2: {e}"
        except Exception as e:
            _LOGGER.error(
                f"Could not check water-state: {e} with extended {ee}")

    def _is_below_start_threshold(self) -> bool:
        return all([
            self._hvac.hub.offset.current_offset >= 0,
            datetime.now().minute >= 30,
            self._hvac.hub.sensors.peaqev_facade.below_start_threshold])

    def _is_price_below_min_price(self) -> bool:
        return float(self._hvac.hub.nordpool.state) <= float(self._hvac.hub.sensors.peaqev_facade.min_price)

    def _set_water_heater_operation_away(self):
        if self._hvac.hub.sensors.peaqev_installed:
            if float(self._hvac.hub.sensors.peaqev_facade.exact_threshold) >= 100:
                self._set_boost(False)
        try:
            if self._hvac.hub.offset.current_offset > 0 and 20 < datetime.now().minute < 50:
                if 0 < self.current_temperature <= LOWTEMP_THRESHOLD:
                    self.model.pre_heating.value = True
                    self._toggle_boost(timer_timeout=None)
        except Exception as e:
            _LOGGER.debug(
                f"Could not properly update water operation in away-mode: {e}"
            )

    def _toggle_boost(self, timer_timeout: int = None) -> None:
        if self.model.try_heat_water.value:
            if self.model.heat_water_timer.is_timeout():
                self._set_boost(False)
        elif all(
                [
                    self.model.pre_heating.value,
                    self._wait_timer.is_timeout(),
                ]
        ):
            self._set_boost(True, timer_timeout)

    def _set_boost(self, set_boost_value:bool, timer_timeout = None) -> None:
        self.model.try_heat_water.value = set_boost_value
        if set_boost_value:
            self.model.latest_boost_call = time.time()
            if timer_timeout:
                self.model.heat_water_timer.update(timer_timeout)
            self.model.try_heat_water.timeout(datetime.now())
        else:
            self._wait_timer.update()
            self.model.pre_heating.value = False
        self._hvac.hub.observer.broadcast("update operation")

