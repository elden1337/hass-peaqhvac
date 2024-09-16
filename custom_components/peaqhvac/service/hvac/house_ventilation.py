import time
from datetime import datetime, timedelta
import logging

from peaqevcore.common.models.observer_types import ObserverTypes
from peaqevcore.models.hub.hubmember import HubMember

from custom_components.peaqhvac.service.hvac.const import WAITTIMER_TIMEOUT, WAITTIMER_VENT
from peaqevcore.common.wait_timer import WaitTimer
from custom_components.peaqhvac.service.models.enums.hvac_presets import HvacPresets
from homeassistant.helpers.event import async_track_time_interval

from custom_components.peaqhvac.service.models.enums.hvacoperations import HvacOperations

_LOGGER = logging.getLogger(__name__)


class HouseVentilation:
    def __init__(self, hvac, observer):
        self.observer = observer
        self._hvac = hvac
        self._wait_timer_boost = WaitTimer(timeout=WAITTIMER_VENT, init_now=False)
        self._current_vent_state: bool = False
        self._latest_seen_fan_speed: float = 0
        self._control_module: HubMember = HubMember(data_type=bool, initval=False)
        async_track_time_interval(self._hvac.hub.state_machine, self.async_check_vent_boost, timedelta(seconds=30))

    @property
    def control_module(self) -> bool:
        return self._control_module.value

    @control_module.setter
    def control_module(self, val) -> None:
        self._control_module.value = val

    @property
    def vent_boost(self) -> bool:
        self._check_hvac_fan_speed()
        return self._current_vent_state

    @vent_boost.setter
    def vent_boost(self, val) -> None:
        if isinstance(val, bool):
            self._current_vent_state = val

    @property
    def booster_update(self) -> bool:
        return (self._hvac.fan_speed >= 3) != self._current_vent_state

    def _check_hvac_fan_speed(self) -> None:
        if self._hvac.fan_speed != self._latest_seen_fan_speed:
            _LOGGER.debug("hvac ventilation speed changed from %s to %s", self._latest_seen_fan_speed, self._hvac.fan_speed)
            if self._latest_seen_fan_speed > self._hvac.fan_speed:
                """Decreased"""
                self._current_vent_state = False
                self.broadcast_changes()
            self._latest_seen_fan_speed = self._hvac.fan_speed

    async def async_check_vent_boost(self, caller=None) -> None:
        if self._hvac.hub.sensors.temp_trend_indoors.samples > 0 and time.time() - self._wait_timer_boost.value > WAITTIMER_VENT:
            if self._vent_boost_warmth():
                await self.async_vent_boost_start("Vent boosting because of warmth.")
                return
            if self._vent_boost_night_cooling():
                await self.async_vent_boost_start("Vent boost night cooling")
                return
            if self._vent_boost_low_dm():
                await self.async_vent_boost_start("Vent boosting because of low degree minutes.")
                return
        if any([
            (self._hvac.hvac_dm > self._hvac.hub.options.heating_options.low_degree_minutes + 100 and self._hvac.hub.sensors.average_temp_outdoors.value < self._hvac.hub.options.heating_options.outdoor_temp_stop_heating),
            self._hvac.hub.sensors.average_temp_outdoors.value < self._hvac.hub.options.heating_options.very_cold_temp
            ]) and self.vent_boost:
            _LOGGER.debug(f"recovered dm or very cold. stopping went boost. dm: {self._hvac.hvac_dm} > {self._hvac.hub.options.heating_options.low_degree_minutes + 100}, temp: {self._hvac.hub.sensors.average_temp_outdoors.value}")
            self.vent_boost = False
            await self.async_broadcast_changes()

    def _vent_boost_warmth(self) -> bool:
        return all(
                    [
                        self._hvac.hub.sensors.get_tempdiff() > 4,
                        self._hvac.hub.sensors.get_tempdiff_in_out() > 5,
                        self._hvac.hub.sensors.temp_trend_indoors.gradient >= 0,
                        self._hvac.hub.sensors.temp_trend_outdoors.gradient >= 0,
                        datetime.now().hour in list(range(7, 21)),
                        self._hvac.hub.sensors.average_temp_outdoors.value >= self._hvac.hub.options.heating_options.outdoor_temp_stop_heating,
                        self._hvac.hub.sensors.set_temp_indoors.preset != HvacPresets.Away,
                    ]
                )

    def _vent_boost_night_cooling(self) -> bool:
        return all(
                    [
                        self._hvac.hub.sensors.get_tempdiff() > 4,
                        self._hvac.hub.sensors.get_tempdiff_in_out() > 5,
                        self._hvac.hub.sensors.average_temp_outdoors.value >= self._hvac.hub.options.heating_options.outdoor_temp_stop_heating,
                        datetime.now().hour in list(range(21, 24)) + list(range(0, 7)),
                        self._hvac.hub.sensors.set_temp_indoors.preset != HvacPresets.Away,
                    ]
                )



    def _vent_boost_low_dm(self) -> bool:
        return all(
                    [
                        self._hvac.hvac_dm <= self._hvac.hub.options.heating_options.low_degree_minutes,
                        self._hvac.hub.sensors.average_temp_outdoors.value >= self._hvac.hub.options.heating_options.very_cold_temp,
                    ]
                )

    async def async_vent_boost_start(self, msg) -> None:
        if not self.vent_boost and self.control_module:
            _LOGGER.debug(msg)
            self._wait_timer_boost.update()
            self.vent_boost = True
            await self.async_broadcast_changes()

    async def async_broadcast_changes(self):
        await self.observer.async_broadcast(
            command=ObserverTypes.UpdateOperation,
            argument=(HvacOperations.VentBoost, int(self.vent_boost))
        )

    def broadcast_changes(self):
        self.observer.broadcast(
            command=ObserverTypes.UpdateOperation,
            argument=(HvacOperations.VentBoost, int(self.vent_boost))
        )