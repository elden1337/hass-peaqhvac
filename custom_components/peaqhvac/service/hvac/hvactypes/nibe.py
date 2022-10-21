import logging
from typing import Tuple

from custom_components.peaqhvac.service.hvac.ihvac import IHvac
from custom_components.peaqhvac.service.models.hvacmode import HvacMode
from custom_components.peaqhvac.service.models.hvacoperations import HvacOperations
from custom_components.peaqhvac.service.models.sensortypes import SensorType

_LOGGER = logging.getLogger(__name__)


class Nibe(IHvac):
    domain = "Nibe"

    _servicecall_types = {
        HvacOperations.Offset:     47011,
        HvacOperations.VentBoost:  "ventilation_boost",
        HvacOperations.WaterBoost: "hot_water_boost"
    }

    def get_sensor(self, getsensor: SensorType = None):
        types = {
            SensorType.HvacMode: f"climate.nibe_{self.hub.options.systemid}_s1_supply|hvac_action",
            SensorType.Offset: f"climate.nibe_{self.hub.options.systemid}_s1_supply|offset_heat",
            SensorType.DegreeMinutes: f"sensor.nibe_{self.hub.options.systemid}_43005",
            SensorType.WaterTemp: f"water_heater.nibe_{self.hub.options.systemid}_40014_47387|current_temperature",
            SensorType.ElectricalAddition: f"sensor.nibe_{self.hub.options.systemid}_43084",
            SensorType.CompressorFrequency: f"sensor.nibe_{self.hub.options.systemid}_43136",
            SensorType.DMCompressorStart: f"sensor.nibe_{self.hub.options.systemid}_47206"
        }
        return types[getsensor] if getsensor is not None else self._get_sensors_for_callback(types)

    @property
    def hvac_mode(self) -> HvacMode:
        sensor = self.get_sensor(SensorType.HvacMode)
        ret = self._handle_sensor(sensor)
        if ret is not None:
            if ret == "heating":
                _LOGGER.debug("hvac mode is heating")
                return HvacMode.Heat
            elif ret == "idle":
                _LOGGER.debug("hvac mode is idle")
                return HvacMode.Idle
        else:
            _LOGGER.debug("could not get hvac mode from hvac")
        return HvacMode.Unknown

    async def _get_operation_value(self, operation: HvacOperations, set_val: any = None):
        _value = None
        match operation:
            case HvacOperations.Offset:
                _value = await self._set_offset_value(set_val)
            case HvacOperations.VentBoost:
                _value = set_val
            case HvacOperations.WaterBoost:
                _value = set_val
        return _value

    async def _get_operation_call_parameters(self, operation: HvacOperations, _value: any) -> Tuple[str, dict, str]:
        call_operation = "set_parameter"
        params = {
            "system":    int(self.hub.options.systemid),
            "parameter": self._servicecall_types[operation],
            "value":     _value
        }
        return call_operation, params, self.domain

    async def _set_offset_value(self, val: int):
        if abs(val) <= 10:
            return val
        return 10 if val > 10 else -10

