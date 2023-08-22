from dataclasses import dataclass

from custom_components.peaqhvac.service.hvac.const import DEFAULT_WATER_BOOST
from custom_components.peaqhvac.service.hvac.wait_timer import WaitTimer


@dataclass
class WaterBoosterModel:
    try_heat_water: bool = False
    heat_water_timer = WaitTimer(timeout=DEFAULT_WATER_BOOST)
    pre_heating: bool = False
    boost: bool = False

    #currently_heating: bool = False