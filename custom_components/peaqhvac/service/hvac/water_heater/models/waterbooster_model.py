from custom_components.peaqhvac.service.hvac.const import DEFAULT_WATER_BOOST
from peaqevcore.common.wait_timer import WaitTimer
from datetime import datetime

from custom_components.peaqhvac.service.observer.event_property import EventProperty


class BusFireOnceMixin:
    _event_log = []

    def bus_fire_once(self, event, data, next_start=None):
        if next_start not in self._event_log:
            self._hass.bus.fire(event, data)
            if next_start:
                self._event_log.append(next_start)


class WaterBoosterModel(BusFireOnceMixin):
    def __init__(self, hass):
        self._hass = hass
        self.heat_water_timer = WaitTimer(timeout=DEFAULT_WATER_BOOST, init_now=False)
        self.water_boost = EventProperty("try_heat_water", bool, hass, False)
        self.next_water_heater_start: datetime = datetime.max
        self.latest_boost_call: int = 0
