from dataclasses import dataclass

from custom_components.peaqhvac.service.hvac.wait_timer import WaitTimer

DEFAULT_WATER_BOOST = 600


@dataclass
class WaterBoosterModel:
    try_heat_water: bool = False
    heat_water_timer = WaitTimer(timeout=DEFAULT_WATER_BOOST)
    pre_heating: bool = False
    boost: bool = False
    water_is_heating: bool = False
