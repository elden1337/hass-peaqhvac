from dataclasses import dataclass, field
from typing import List
from custom_components.peaqhvac.const import HVACBRAND_NIBE, HVACBRAND_THERMIA, HVACBRAND_IVT
from custom_components.peaqhvac.service.models.enums.hvacbrands import HvacBrand

@dataclass
class MiscOptions:
    enabled_on_boot: bool = True

@dataclass
class ConfigModel:
    misc_options: MiscOptions = MiscOptions()
    indoor_tempsensors: List = field(default_factory=lambda: [])
    outdoor_tempsensors: List = field(default_factory=lambda: [])
    hvacbrand: HvacBrand = field(init=False)
    systemid:str = field(init=False)
    hvac_tolerance: int = 0

    def set_hvacbrand(self, configstring: str) -> HvacBrand:
        branddict = {
            HVACBRAND_NIBE: HvacBrand.Nibe,
            HVACBRAND_IVT: HvacBrand.IVT,
            HVACBRAND_THERMIA: HvacBrand.Thermia
        }
        return branddict[configstring]

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

