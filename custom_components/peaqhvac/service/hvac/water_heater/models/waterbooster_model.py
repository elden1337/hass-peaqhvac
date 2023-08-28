from custom_components.peaqhvac.service.hvac.const import DEFAULT_WATER_BOOST
from peaqevcore.common.wait_timer import WaitTimer

from custom_components.peaqhvac.service.observer.event_property import EventProperty


class WaterBoosterModel:
    def __init__(self, hass):
        self._hass = hass
        self.heat_water_timer = WaitTimer(timeout=DEFAULT_WATER_BOOST, init_now=False)
        self.pre_heating = EventProperty("pre_heating", bool, hass) #kan vara issuet
        #self.boost = EventProperty("boost", bool, hass)
        #self.currently_heating = EventProperty("currently_heating", bool, hass)
        self.try_heat_water = EventProperty("try_heat_water", bool, hass)

        self.pre_heating.value = False
        #self.boost.value = False
        #self.currently_heating.value = False
        self.try_heat_water.value = False