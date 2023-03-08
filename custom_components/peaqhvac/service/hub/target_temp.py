from typing import Tuple
import logging
from custom_components.peaqhvac.service.models.enums.hvac_presets import HvacPresets
from custom_components.peaqhvac.service.observer import ObserverBroadcaster

MINTEMP = 15
MAXTEMP = 27
_LOGGER = logging.getLogger(__name__)


class TargetTemp(ObserverBroadcaster):
    def __init__(self, initval=19, observer_message:str = None, hub = None):
        self.hub = hub
        self._value = initval
        self._min_tolerance = None
        self._max_tolerance = None
        self._preset = HvacPresets.Normal
        self._internal_set_temp = initval
        super().__init__(observer_message, hub)
        self._set_temperature_and_tolerances()

    @property
    def min_tolerance(self) -> float:
        return self._min_tolerance

    @property
    def max_tolerance(self) -> float:
        return self._max_tolerance

    @property
    def value(self) -> float:
        return self._value

    @value.setter
    def value(self, val) -> None:
        try:
            if val is not None:
                self._value = val
            self._internal_set_temp = self._value - HvacPresets.get_tempdiff(self.preset)
            self._set_temperature_and_tolerances()
            self._broadcast_changes()
        except:
            _LOGGER.error(f"Unable to set the targettemp value. The incoming val is {val}")

    @property
    def preset(self) -> HvacPresets:
        return self._preset

    @preset.setter
    def preset(self, val):
        old_preset = self._preset
        self._preset = HvacPresets.get_type(val)
        if old_preset != self._preset:
            self.hub.observer.broadcast("hvac preset changed")
        self._set_temperature_and_tolerances()

    def _set_temperature_and_tolerances(self):
        self._init_set_temp(preset=self.preset)
        self._init_tolerances(preset=self.preset)

    def _init_set_temp(self, preset: HvacPresets = HvacPresets.Normal):
        _tempdiff = HvacPresets.get_tempdiff(preset)
        self._value = self._minmax(self._internal_set_temp + _tempdiff)

    def _init_tolerances(self, preset: HvacPresets = HvacPresets.Normal):
        _tolerances = HvacPresets.get_tolerances(preset)
        self._min_tolerance = _tolerances[0]
        self._max_tolerance = _tolerances[1]

    def adjusted_set_temp(self) -> float:
        """adjust the set temp slightly if below -5C outside"""
        ret = self.value
        _outdoors = self.hub.sensors.average_temp_outdoors.value
        if _outdoors < -5 and self.preset is not HvacPresets.Normal:
            ret += round(((int(_outdoors - -5) / 1.5) * 0.1), 1)
        return max(ret, 15)

    def adjusted_tolerances(self, offset: int) -> Tuple[float, float]:
        _max_tolerance = self.max_tolerance + (offset / 10) if offset > 0 else self.max_tolerance
        _min_tolerance = self.min_tolerance + (abs(offset) / 10) if offset < 0 else self.min_tolerance
        return max(_min_tolerance, 0.1), max(_max_tolerance, 0.1)

    def _minmax(self, desired_temp) -> float:
        if desired_temp < MINTEMP:
            return MINTEMP
        if desired_temp > MAXTEMP:
            return MAXTEMP
        return desired_temp