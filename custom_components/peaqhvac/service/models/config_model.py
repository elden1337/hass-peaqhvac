import logging
from dataclasses import dataclass, field
from typing import List

from peaqevcore.common.models.observer_types import ObserverTypes

from custom_components.peaqhvac.const import (HVACBRAND_IVT, HVACBRAND_NIBE,
                                              HVACBRAND_THERMIA)
from custom_components.peaqhvac.service.models.enums.hvacbrands import \
    HvacBrand

_LOGGER = logging.getLogger(__name__)


@dataclass
class MiscOptions:
    enabled_on_boot: bool = True


@dataclass
class HeatingOptions:
    outdoor_temp_stop_heating: int = 999
    non_hours_water_boost: list[int] = field(default_factory=lambda: [])
    demand_hours_water_boost: list[int] = field(default_factory=lambda: [])
    low_degree_minutes: int = -9999
    very_cold_temp: int = -999


class ConfigModel:
    misc_options: MiscOptions = MiscOptions()
    heating_options: HeatingOptions = HeatingOptions()
    indoor_tempsensors: List = field(default_factory=lambda: [])
    outdoor_tempsensors: List = field(default_factory=lambda: [])
    hvacbrand: HvacBrand = field(init=False)
    systemid: str = field(init=False)
    _hvac_tolerance: int = None
    hub = None

    @property
    def hvac_tolerance(self) -> int:
        return self._hvac_tolerance

    @hvac_tolerance.setter
    def hvac_tolerance(self, val) -> None:
        if self._hvac_tolerance != val:
            self._hvac_tolerance = val
            if self.hub is not None:
                self.hub.observer.broadcast(ObserverTypes.HvacToleranceChanged, self._hvac_tolerance)
                self.hub.observer.broadcast("OffsetPrecalculation")
            else:
                _LOGGER.warning(
                    "tried to broadcast an update from hvac-tolerance but referenced hub was None."
                )

    def set_hvacbrand(self, configstring: str) -> HvacBrand:
        branddict = {
            HVACBRAND_NIBE: HvacBrand.Nibe,
            HVACBRAND_IVT: HvacBrand.IVT,
            HVACBRAND_THERMIA: HvacBrand.Thermia,
        }
        return branddict[configstring]

    def set_sensors_from_string(self, inputstr: str) -> list:
        input_list = inputstr.split(",")
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
