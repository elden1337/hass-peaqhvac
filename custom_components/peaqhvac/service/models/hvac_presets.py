from homeassistant.components.climate.const import (
    PRESET_NONE,
    PRESET_ECO,
    PRESET_AWAY
)
from enum import Enum


class HvacPresets(Enum):
    Normal = 1
    Eco = 2
    Away = 3
    ExtendedAway = 4

    @staticmethod
    def get_type(ha_preset: str):
        types = {
            PRESET_NONE: HvacPresets.Normal,
            PRESET_AWAY: HvacPresets.Away,
            PRESET_ECO:  HvacPresets.Eco
        }
        return types[ha_preset]

    @staticmethod
    def get_tolerances(preset):
        types = {
            HvacPresets.Normal:       (0.5, 1),
            HvacPresets.Eco:          (1, 0.5),
            HvacPresets.Away:         (1, 0),
            HvacPresets.ExtendedAway: (1, 0)
        }
        return types[preset]