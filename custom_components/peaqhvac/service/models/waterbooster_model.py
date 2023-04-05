from dataclasses import dataclass

DEFAULT_WATER_BOOST = 600


@dataclass
class WaterBoosterModel:
    try_heat_water: bool = False
    heat_water_timer: int = 0
    heat_water_timer_timeout = DEFAULT_WATER_BOOST
    pre_heating: bool = False
    boost: bool = False
    water_is_heating: bool = False
