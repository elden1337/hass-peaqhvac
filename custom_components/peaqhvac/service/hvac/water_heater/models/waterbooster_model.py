from custom_components.peaqhvac.service.hvac.const import DEFAULT_WATER_BOOST
from custom_components.peaqhvac.service.hvac.wait_timer import WaitTimer


class EventProperty:
    def __init__(self, name, prop_type: type, hub):
        self._value = None
        self._hub = hub
        self.name = name
        self._prop_type = prop_type

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, val):
        if self._value != val:
            self._value = val
            #self._hub.sensors.peaqev_facade.publish_observer_message(f"{self.name}_changed", val)
            self._hub.hass.bus.fire(f"peaqhvac.{self.name}_changed", {"new": val})


class WaterBoosterModel:
    def __init__(self, hass):
        self._hass = hass
        self.heat_water_timer = WaitTimer(timeout=DEFAULT_WATER_BOOST)
        self.pre_heating = EventProperty("pre_heating", bool, hass)
        self.boost = EventProperty("boost", bool, hass)
        self.currently_heating = EventProperty("currently_heating", bool, hass)
        self.try_heat_water = EventProperty("try_heat_water", bool, hass)

        self.pre_heating.value = False
        self.boost.value = False
        self.currently_heating.value = False
        self.try_heat_water.value = False




    #currently_heating: bool = False