import logging
from typing import Tuple

from custom_components.peaqhvac.service.hvac.interfaces.ihvac import IHvac
from custom_components.peaqhvac.service.models.enums.hvacmode import HvacMode
from custom_components.peaqhvac.service.models.enums.hvacoperations import \
    HvacOperations
from custom_components.peaqhvac.service.models.enums.sensortypes import \
    SensorType

_LOGGER = logging.getLogger(__name__)

NIBE_MAX_THRESHOLD = 10
NIBE_MIN_THRESHOLD = -10
class Nibe(IHvac):
    domain = "Nibe"
    water_heater_entity = None

    _servicecall_types = {
        HvacOperations.Offset: 47011,
        HvacOperations.VentBoost: "ventilation_boost",
        HvacOperations.WaterBoost: "hot_water_boost",
    }

    def _get_water_heater(self) -> str:
        """Fix to handle both new and old water heater entity naming."""
        if self.water_heater_entity:
            return self.water_heater_entity
        try:
            w1 = self.hub.state_machine.states.get(f"water_heater.nibe_{self.hub.options.systemid}_40014_47387")
            if w1:
                attr1 = w1.attributes.get("current_temperature")
                if attr1:
                    self.water_heater_entity = f"water_heater.nibe_{self.hub.options.systemid}_40014_47387|current_temperature"
                    _LOGGER.debug(f"Found water_heater entity: {self.water_heater_entity}")
                    return self.water_heater_entity
            w2 = self.hub.state_machine.states.get(f"water_heater.nibe_hot_water")
            if w2:
                attr2 = w2.attributes.get("current_temperature")
                if attr2:
                    self.water_heater_entity = f"water_heater.nibe_hot_water|current_temperature"
                    _LOGGER.debug(f"Found water_heater entity: {self.water_heater_entity}")
                    return self.water_heater_entity
        except Exception as e:
            _LOGGER.error("Unable to set water_heater_entity", e)
            return None

    def get_sensor(self, sensor: SensorType = None):
        types = {
            SensorType.HvacMode: f"climate.nibe_{self.hub.options.systemid}_s1_supply|hvac_action",
            SensorType.Offset: f"climate.nibe_{self.hub.options.systemid}_s1_supply|offset_heat",
            SensorType.DegreeMinutes: f"sensor.nibe_{self.hub.options.systemid}_43005",
            SensorType.WaterTemp: self._get_water_heater(),
            SensorType.HvacTemp: f"climate.nibe_{self.hub.options.systemid}_s1_supply|current_temperature",
            SensorType.CondenserReturn: f"sensor.nibe_{self.hub.options.systemid}_40012",
            SensorType.ElectricalAddition: f"sensor.nibe_{self.hub.options.systemid}_43084",
            SensorType.CompressorFrequency: f"sensor.nibe_{self.hub.options.systemid}_43136",
            SensorType.DMCompressorStart: f"sensor.nibe_{self.hub.options.systemid}_47206",
            SensorType.FanSpeed: f"sensor.nibe_{self.hub.options.systemid}_10001|raw_value",
        }
        return (
            types[sensor]
            if sensor is not None
            else self._get_sensors_for_callback(types)
        )

    @property
    def fan_speed(self) -> float:
        try:
            speed = self.get_sensor(SensorType.FanSpeed)
            return float(self._handle_sensor(speed))
        except Exception as e:
            _LOGGER.debug(f"Unable to get fan speed: {e}")
            return 0

    @property
    def delta_return_temp(self):
        try:
            temp = self.get_sensor(SensorType.HvacTemp)
            returntemp = self.get_sensor(SensorType.CondenserReturn)
            return round(float(self._handle_sensor(temp)) - float(self._handle_sensor(returntemp)),2,)
        except Exception as e:
            _LOGGER.debug(f"Unable to calculate delta return: {e}")
            return 0

    @property
    def hvac_mode(self) -> HvacMode:
        sensor = self.get_sensor(SensorType.HvacMode)
        ret = self._handle_sensor(sensor)
        if ret is not None:
            if ret == "heating":
                return HvacMode.Heat
            elif ret == "idle":
                return HvacMode.Idle
        return HvacMode.Unknown

    async def _get_operation_value(
        self, operation: HvacOperations, set_val: any = None
    ):
        match operation:
            case HvacOperations.Offset:
                return self._cap_nibe_offset_value(set_val)
            case HvacOperations.VentBoost | HvacOperations.WaterBoost:
                return set_val
        raise ValueError(f"Operation {operation} not supported")

    def _set_operation_call_parameters(
        self, operation: HvacOperations, _value: any
    ) -> Tuple[str, dict, str]:
        call_operation = "set_parameter"
        params = {
            "system": int(self.hub.options.systemid),
            "parameter": self._servicecall_types[operation],
            "value": int(_value),
        }
        return call_operation, params, self.domain

    @staticmethod
    def _cap_nibe_offset_value(val: int):
        """Nibe only supports offsets between -10 and 10"""
        if abs(val) <= NIBE_MAX_THRESHOLD:
            return val
        return NIBE_MAX_THRESHOLD if val > NIBE_MAX_THRESHOLD else NIBE_MIN_THRESHOLD
