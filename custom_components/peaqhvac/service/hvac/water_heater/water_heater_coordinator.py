import logging
import time
from datetime import datetime

import custom_components.peaqhvac.extensionmethods as ex
from custom_components.peaqhvac.service.hub.trend import Gradient
from custom_components.peaqhvac.service.hvac.interfaces.iheater import IHeater
from custom_components.peaqhvac.service.hvac.wait_timer import WaitTimer
from custom_components.peaqhvac.service.hvac.water_heater.water_peak import get_water_peak
from custom_components.peaqhvac.service.models.enums.demand import Demand
from custom_components.peaqhvac.service.models.enums.hvac_presets import \
    HvacPresets
from custom_components.peaqhvac.service.models.waterbooster_model import \
    WaterBoosterModel

_LOGGER = logging.getLogger(__name__)

WAITTIMER_TIMEOUT = 1800
LOWTEMP_THRESHOLD = 25
HIGHTEMP_THRESHOLD = 42


class WaterHeater(IHeater):
    def __init__(self, hvac):
        self._hvac = hvac
        super().__init__(hvac=hvac)
        self._current_temp = None
        self._wait_timer = WaitTimer(timeout=WAITTIMER_TIMEOUT)
        self._wait_timer_peak = WaitTimer(timeout=WAITTIMER_TIMEOUT)
        self._temp_trend = Gradient(
            max_age=3600, max_samples=10, precision=0, ignore=0
        )
        self.booster_model = WaterBoosterModel()
        self._hvac.hub.observer.add("offset recalculation", self.update_operation)

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
        if self.booster_model.heat_water_timer.value > 0:
            return ex.dt_from_epoch(self.booster_model.heat_water_timer.value)
        return "-"

    @latest_boost_call.setter
    def latest_boost_call(self, val):
        self.booster_model.heat_water_timer.update()

    @property
    def current_temperature(self) -> float:
        """The current reported water-temperature in the hvac"""
        return self._current_temp

    @current_temperature.setter
    def current_temperature(self, val):
        try:
            if self._current_temp != float(val):
                self._current_temp = float(val)
                self._temp_trend.add_reading(val=float(val), t=time.time())
                self._hvac.hub.observer.broadcast("watertemp change")
                self.update_operation()
        except ValueError as E:
            _LOGGER.warning(f"unable to set {val} as watertemperature. {E}")
            self.booster_model.try_heat_water = False

    @IHeater.demand.setter
    def demand(self, val):
        self._demand = val

    @property
    def try_heat_water(self) -> bool:
        """Returns true if we should try and heat the water"""
        return self.booster_model.try_heat_water

    @property
    def water_heating(self) -> bool:
        """Return true if the water is currently being heated"""
        return self.temperature_trend > 0 or self.booster_model.pre_heating is True

    async def async_get_demand(self) -> Demand:
        temp = self.current_temperature
        if temp is None:
            return Demand.NoDemand
        if 0 < temp < 100:
            if temp >= 42:
                return Demand.NoDemand
            if temp > 35:
                return Demand.LowDemand
            if temp >= 25:
                return Demand.MediumDemand
            if temp < 25:
                return Demand.HighDemand
        return Demand.NoDemand

    def _get_water_peak(self, hour: int) -> bool:
        if self._wait_timer_peak.is_timeout() and self._hvac.hub.is_initialized:
            _prices = self._get_pricelist_combined()
            avg_monthly = None
            if self._hvac.hub.sensors.peaqev_installed:
                avg_monthly = self._hvac.hub.sensors.peaqev_facade.average_this_month
            ret = get_water_peak(hour, _prices, avg_monthly)
            if ret:
                self._wait_timer_peak.update()
            return ret
        return False

    async def async_get_water_peak(self, hour: int) -> bool:
        return self._get_water_peak(hour)

    def _get_pricelist_combined(self) -> list:
        _prices = self._hvac.hub.nordpool.prices
        if self._hvac.hub.nordpool.prices_tomorrow is not None:
            _prices.extend(
                [
                    p
                    for p in self._hvac.hub.nordpool.prices_tomorrow
                    if isinstance(p, (float, int))
                ]
            )
        return _prices

    async def async_update_operation(self):
        if self.is_initialized:
            if self._hvac.hub.sensors.set_temp_indoors.preset != HvacPresets.Away:
                await self.async_set_water_heater_operation_home()
            elif self._hvac.hub.sensors.set_temp_indoors.preset == HvacPresets.Away:
                await self.async_set_water_heater_operation_away()

    def update_operation(self):
        if self.is_initialized:
            if self._hvac.hub.sensors.set_temp_indoors.preset != HvacPresets.Away:
                self._set_water_heater_operation_home()
            elif self._hvac.hub.sensors.set_temp_indoors.preset == HvacPresets.Away:
                self._set_water_heater_operation_away()

    def _set_water_heater_operation_home(self) -> None:
        if self._hvac.hub.sensors.peaqev_installed:
            if all([
                float(self._hvac.hub.sensors.peaqev_facade.exact_threshold) >= 100,
                self.booster_model.try_heat_water]):
                _LOGGER.debug("Peak is being breached. Turning off water heating")
                self._turn_off_boost()
        try:
            if self._get_water_peak(datetime.now().hour):
                _LOGGER.debug("Current hour is identified as a good hour to boost water")
                self.booster_model.boost = True
                self._toggle_boost(timer_timeout=3600)
            elif any([
                self._get_current_offset() > 0,
                float(self._hvac.hub.nordpool.state) <= float(self._hvac.hub.sensors.peaqev_facade.min_price)
            ]):
                self._toggle_hotwater_boost(HIGHTEMP_THRESHOLD)
        except Exception as e:
            _LOGGER.error(
                f"Could not check water-state: {e}. nordpool-state: {self._hvac.hub.nordpool.state}, min-price: {self._hvac.hub.sensors.peaqev_facade.min_price}")
            return

    async def async_set_water_heater_operation_home(self) -> None:
        self._set_water_heater_operation_home()

    def _set_water_heater_operation_away(self):
        if self._hvac.hub.sensors.peaqev_installed:
            if float(self._hvac.hub.sensors.peaqev_facade.exact_threshold) >= 100:
                self._turn_off_boost()
        try:
            if self._get_current_offset() > 0 and 10 < datetime.now().minute < 50:
                if 0 < self.current_temperature <= LOWTEMP_THRESHOLD:
                    self.booster_model.pre_heating = True
                    self._toggle_boost(timer_timeout=None)
        except Exception as e:
            _LOGGER.debug(
                f"Could not properly update water operation in away-mode: {e}"
            )

    def _toggle_hotwater_boost(self, temp_threshold):
        if all(
            [0 < self.current_temperature <= temp_threshold, datetime.now().minute > 10]
        ):
            self.booster_model.pre_heating = True
            self._toggle_boost(timer_timeout=None)
        else:
            self.booster_model.pre_heating = False

    def _get_current_offset(self) -> int:
        offsets = self._hvac.hub.offset.get_raw_offset()
        return offsets[0].get(datetime.now().hour, 0)

    async def async_get_current_offset(self) -> int:
        offsets = await self._hvac.hub.offset.async_get_raw_offset()
        return offsets[0].get(datetime.now().hour, 0)



    async def async_set_water_heater_operation_away(self):
        self._set_water_heater_operation_away()

    def _toggle_boost(self, timer_timeout: int = None) -> None:
        if self.booster_model.try_heat_water:
            if self.booster_model.heat_water_timer.timeout > 0:
                if self.booster_model.heat_water_timer.is_timeout():
                    self._turn_off_boost()
        elif all(
                [
                    any([self.booster_model.pre_heating, self.booster_model.boost]),
                    self._wait_timer.is_timeout(),
                ]
        ):
            self._turn_on_boost(timer_timeout)

    def _turn_on_boost(self, timer_timeout = None) -> None:
        self.booster_model.try_heat_water = True
        self.booster_model.heat_water_timer_timeout.update(timer_timeout)
        self._hvac.hub.observer.broadcast("update operation")

    def _turn_off_boost(self) -> None:
        self.booster_model.try_heat_water = False
        self._wait_timer.update()
        self._hvac.hub.observer.broadcast("update operation")