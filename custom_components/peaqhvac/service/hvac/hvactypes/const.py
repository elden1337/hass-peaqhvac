from custom_components.peaqhvac.service.models.enums.hvacmode import HvacMode
from custom_components.peaqhvac.service.models.enums.hvacoperations import HvacOperations

ADDON_VALUE_CONVERSION = {
            "Alarm":   False,
            "Blocked": False,
            "Off":     False,
            "Active":  True,
        }

HVACMODE_LOOKUP = {
            "Off":       HvacMode.Idle,
            "Hot water": HvacMode.Water,
            "Heating":   HvacMode.Heat,
        }
