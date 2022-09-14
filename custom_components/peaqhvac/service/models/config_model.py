from dataclasses import dataclass, field
from typing import List, Dict

from enum import Enum

class HvacBrand(Enum):
    Nibe = 1
    IVT = 2
    Thermia = 3

@dataclass
class ConfigModel:
    indoor_tempsensors: List = field(default_factory=lambda: [])
    outdoor_tempsensors: List = field(default_factory=lambda: [])
    hvacbrand: HvacBrand = field(init=False)
    systemid:str = field(init=False)
    hvac_tolerance: int = 0


