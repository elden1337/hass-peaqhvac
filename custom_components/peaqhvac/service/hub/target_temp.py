from custom_components.peaqhvac.service.models.hvac_presets import HvacPresets


class TargetTemp:
    def __init__(self, initval=20):
        self._value = initval
        self._min_tolerance = None
        self._max_tolerance = None
        self._preset = HvacPresets.Normal
        self.init_tolerances()

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
        self.init_tolerances(self._preset)

    @property
    def preset(self) -> HvacPresets:
        return self._preset

    @preset.setter
    def preset(self, val):
        self._preset = val
        self.set_tolerances(val)

    def set_tolerances(self, ha_preset: str):
        self._preset = HvacPresets.get_type(ha_preset)
        self.init_tolerances(preset=self._preset)

    def init_tolerances(self, preset: HvacPresets = HvacPresets.Normal):
        _tolerances = HvacPresets.get_tolerances(preset)
        self._min_tolerance = _tolerances[0]
        self._max_tolerance = _tolerances[1]