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

    def set_sensors_from_string(self, inputstr: str) -> list:
        input_list = inputstr.split(',')
        result_list = []
        if len(input_list) > 0:
            for i in input_list:
                result_list.append(self._set_single_sensor(i))
        elif len(inputstr) > 0:
            result_list.append(self._set_single_sensor(inputstr))
        return result_list

    def _set_single_sensor(self, sensor: str):
        ret = sensor
        if not sensor.startswith("sensor."):
            ret = f"sensor.{sensor}"
        return ret

