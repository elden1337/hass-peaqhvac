from dataclasses import dataclass

from custom_components.peaqhvac.service.hvac.const import DEFAULT_WATER_BOOST
from custom_components.peaqhvac.service.hvac.wait_timer import WaitTimer


class EventProperty:
    """A property that notifies hass.bus when changed"""
    def __init__(self, name, prop_type: type):
        self._value = None
        self.name = name
        self._prop_type = prop_type

    @property
    def value(self):
        return self._value

@dataclass
class WaterBoosterModel:
    try_heat_water: bool = False
    heat_water_timer = WaitTimer(timeout=DEFAULT_WATER_BOOST)
    pre_heating: bool = False
    boost: bool = False

    #currently_heating: bool = False