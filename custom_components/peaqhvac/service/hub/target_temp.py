from custom_components.peaqhvac.service.models.hvac_presets import HvacPresets


class TargetTemp:
    def __init__(self, initval=20):
        self._value = initval
        self._min_tolerance = None
        self._max_tolerance = None
        self._preset = HvacPresets.Normal
        self._internal_set_temp = initval
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
        self._value = val
        self._internal_set_temp = val - HvacPresets.get_tempdiff(self.preset)
        self._set_temperature_and_tolerances()

    @property
    def preset(self) -> HvacPresets:
        return self._preset

    @preset.setter
    def preset(self, val):
        self._preset = HvacPresets.get_type(val)
        self._set_temperature_and_tolerances()

    def _set_temperature_and_tolerances(self):
        self._init_set_temp(preset=self.preset)
        self._init_tolerances(preset=self.preset)

    def _init_set_temp(self, preset: HvacPresets = HvacPresets.Normal):
        _tempdiff = HvacPresets.get_tempdiff(preset)
        self._value = self._internal_set_temp + _tempdiff

    def _init_tolerances(self, preset: HvacPresets = HvacPresets.Normal):
        _tolerances = HvacPresets.get_tolerances(preset)
        self._min_tolerance = _tolerances[0]
        self._max_tolerance = _tolerances[1]