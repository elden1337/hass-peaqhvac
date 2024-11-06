import logging

from custom_components.peaqhvac.service.hvac.hvactypes.hvactype import HvacType
from custom_components.peaqhvac.service.models.enums.hvacoperations import HvacOperations
from custom_components.peaqhvac.service.models.enums.sensortypes import SensorType

_LOGGER = logging.getLogger(__name__)

NIBE_MAX_THRESHOLD = 10
NIBE_MIN_THRESHOLD = -10

class Nibe(HvacType):
    domain = "Nibe"
    water_heater_entity = None

    def _servicecall_types(self):
        return {
            HvacOperations.Offset: self.get_sensor(SensorType.Offset),
            HvacOperations.VentBoost: self.get_sensor(SensorType.VentilationBoost),
            HvacOperations.WaterBoost: self.get_sensor(SensorType.HotWaterBoost),
        }

    def get_sensor(self, sensor: SensorType = None):
        types = {
            SensorType.HvacMode: f"sensor.{self.hub.options.systemid}_priority",
            SensorType.Offset: f"number.{self.hub.options.systemid}_heating_offset_climate_system_1",
            SensorType.DegreeMinutes: f"number.{self.hub.options.systemid}_current_value",
            SensorType.WaterTemp: f"sensor.{self.hub.options.systemid}_hot_water_charging_bt6",
            SensorType.HvacTemp: f"sensor.{self.hub.options.systemid}_supply_line_bt2",
            SensorType.HotWaterReturn: f"sensor.{self.hub.options.systemid}_return_line_bt3",
            SensorType.ElectricalAddition: f"sensor.{self.hub.options.systemid}_int_elec_add_heat",
            SensorType.CompressorFrequency: f"sensor.{self.hub.options.systemid}_current_compressor_frequency",
            SensorType.DMCompressorStart: f"number.{self.hub.options.systemid}_start_compressor",
            SensorType.FanSpeed: f"sensor.{self.hub.options.systemid}_current_fan_mode",
            SensorType.HotWaterBoost: f"switch.{self.hub.options.systemid}_temporary_lux",
            SensorType.VentilationBoost: f"switch.{self.hub.options.systemid}_increased_ventilation",
        }
        return (
            types.get(sensor, None)
            if sensor is not None
            else self._get_sensors_for_callback(types)
        )

    @property
    def fan_speed(self) -> float:
        try:
            speed = self.get_sensor(SensorType.FanSpeed)
            return float(self._handle_sensor(speed))
        except Exception as e:
            if "unavailable" not in str(e):
                _LOGGER.exception(e)
            return 0

    @property
    def delta_return_temp(self):
        try:
            temp = self.get_sensor(SensorType.HvacTemp)
            returntemp = self.get_sensor(SensorType.HotWaterReturn)
            return round(float(self._handle_sensor(temp)) - float(self._handle_sensor(returntemp)),2,)
        except Exception as e:
            _LOGGER.debug(f"Unable to calculate delta return: {e}")
            return 0

    def _set_servicecall_params(self, operation, _value):
        ret = {"entity_id": self._servicecall_types()[operation]}
        if operation is HvacOperations.Offset:
            ret["value"] = self._cap_nibe_offset_value(_value)
        return ret

    @staticmethod
    def _cap_nibe_offset_value(val: int) -> int:
        """Nibe only supports offsets between -10 and 10"""
        _LOGGER.debug("Capping nibe offset value", val)
        if abs(val) <= NIBE_MAX_THRESHOLD:
            return val
        return NIBE_MAX_THRESHOLD if val > NIBE_MAX_THRESHOLD else NIBE_MIN_THRESHOLD
