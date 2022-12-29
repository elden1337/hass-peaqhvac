from homeassistant.components.climate.const import (
    PRESET_NONE,
    PRESET_AWAY,
    PRESET_ECO
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
            HvacPresets.Normal:       (0.2, 0.3),
            HvacPresets.Eco:          (0.2, 0.2),
            HvacPresets.Away:         (0.5, 0.2),
            HvacPresets.ExtendedAway: (0.7, 0)
        }
        return types[preset]

    @staticmethod
    def get_tempdiff(preset) -> int:
        types = {
            HvacPresets.Normal:       0,
            HvacPresets.Eco:          0,
            HvacPresets.Away:         -1,
            HvacPresets.ExtendedAway: -2
        }
        return types[preset]
