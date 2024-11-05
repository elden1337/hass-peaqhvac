import logging
from typing import Tuple

from peaqevcore.common.models.observer_types import ObserverTypes

from custom_components.peaqhvac.service.models.enums.hvac_presets import \
    HvacPresets
from custom_components.peaqhvac.service.observer.observer_broadcaster import ObserverBroadcaster

MINTEMP = 15
MAXTEMP = 27
_LOGGER = logging.getLogger(__name__)


def adjusted_tolerances(offset: int, min_tolerance, max_tolerance) -> Tuple[float, float]:
    # if abs(offset) <= 1:
    return min_tolerance, max_tolerance
    # _max_tolerance = (
    #     max_tolerance + (offset / 15) if offset > 0 else max_tolerance
    # )
    # _min_tolerance = (
    #     min_tolerance + (abs(offset) / 10)
    #     if offset < 0
    #     else min_tolerance
    # )
    # return max(_min_tolerance, 0.1), max(_max_tolerance, 0.1)


class TargetTemp(ObserverBroadcaster):
    def __init__(self, initval=19, observer_message: str = None, hub=None):
        self.hub = hub
        self._value = initval
        self._min_tolerance = None
        self._max_tolerance = None
        self._adjusted_value = 0
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
            self._adjusted_value = self.adjusted_temp
            self._set_temperature_and_tolerances()
            self._broadcast_changes()
        except:
            _LOGGER.error(
                f"Unable to set the targettemp value. The incoming val is {val}"
            )

    @property
    def preset(self) -> HvacPresets:
        return self._preset

    @preset.setter
    def preset(self, val):
        old_preset = self._preset
        self._preset = HvacPresets.get_type(val)
        if old_preset != self._preset:
            self.hub.observer.broadcast(ObserverTypes.HvacPresetChanged)
        self._set_temperature_and_tolerances()

    @property
    def adjusted_temp(self) -> float:
        """adjust the set temp slightly if below -5C outside"""
        _frost_temp = -3 if self.preset is not HvacPresets.Normal else -5
        ret = self.value
        _outdoors = self.hub.sensors.average_temp_outdoors.value
        if _outdoors < _frost_temp:
            ret += round(((int(_outdoors - _frost_temp) / 1.5) * 0.1), 1)
            if ret != self._adjusted_value:
                self._adjusted_value = ret
                _LOGGER.info(
                    f"Adjusted the set indoor temperature from {self.value}C to {ret}C due to outdoors being colder than {_frost_temp}C."
                )
        return max(ret, 15)

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



    @staticmethod
    def _minmax(desired_temp) -> float:
        if desired_temp < MINTEMP:
            return MINTEMP
        if desired_temp > MAXTEMP:
            return MAXTEMP
        return desired_temp
