from custom_components.peaqhvac.service.hvac.const import DEFAULT_WATER_BOOST
from peaqevcore.common.wait_timer import WaitTimer
from datetime import datetime

from custom_components.peaqhvac.service.observer.event_property import EventProperty


class WaterBoosterModel:
    def __init__(self, hass):
        self._event_log = []
        self._hass = hass
        self.heat_water_timer = WaitTimer(timeout=DEFAULT_WATER_BOOST, init_now=False)
        self.pre_heating = EventProperty("pre_heating", bool, hass, False) #kan vara issuet
        self.try_heat_water = EventProperty("try_heat_water", bool, hass, False)
        self.next_water_heater_start: datetime = datetime.max        

        #self.boost = EventProperty("boost", bool, hass, False)
        #self.currently_heating = EventProperty("currently_heating", bool, hass, False)

    def bus_fire_once(self, event, data, next_start):
        if next_start not in self._event_log:            
            self._hass.bus.fire(event, data)
            self._event_log.append(next_start)