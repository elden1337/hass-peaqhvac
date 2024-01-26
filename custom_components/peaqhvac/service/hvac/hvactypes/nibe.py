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

    def _servicecall_types(self):
        return {
            HvacOperations.Offset: 47011,
            HvacOperations.VentBoost: self.get_sensor(SensorType.VentilationBoost),
            HvacOperations.WaterBoost: self.get_sensor(SensorType.HotWaterBoost),
        }

#f730_cu_3x400v_magnus_nibef_f730_cu_3x400v
    def get_sensor(self, sensor: SensorType = None):
        types = {
            SensorType.HvacMode: f"sensor.{self.hub.options.systemid}_priority",
            #SensorType.Offset: f"climate.nibe_{self.hub.options.systemid}_s1_supply|offset_heat", #only exists with spa active (ie not usable)
            SensorType.DegreeMinutes: f"sensor.{self.hub.options.systemid}_degree_minutes",
            SensorType.WaterTemp: f"sensor.{self.hub.options.systemid}_hot_water_charging_bt6",
            SensorType.HvacTemp: f"sensor.{self.hub.options.systemid}_supply_line_bt2",
            SensorType.HotWaterReturn: f"sensor.{self.hub.options.systemid}_return_line_bt3",
            SensorType.ElectricalAddition: f"sensor.{self.hub.options.systemid}_int_elec_add_heat",
            SensorType.CompressorFrequency: f"sensor.{self.hub.options.systemid}_current_compressor_frequency",
            #SensorType.DMCompressorStart: f"sensor.nibe_{self.hub.options.systemid}_47206",
            SensorType.FanSpeed: f"sensor.{self.hub.options.systemid}_current_fan_mode",
            SensorType.HotWaterBoost: f"switch.{self.hub.options.systemid}_temporary_lux",
            SensorType.VentilationBoost: f"switch.{self.hub.options.systemid}_increased_ventilation",
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
            #_LOGGER.debug(f"Unable to get fan speed: {e}")
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

    @property
    def hvac_mode(self) -> HvacMode:
        """
            'enumValues': [
          {
            'value': '10',
            'text': 'Off',
            'icon': ''
          },
          {
            'value': '20',
            'text': 'Hot water',
            'icon': ''
          },
          {
            'value': '30',
            'text': 'Heating',
            'icon': ''
          },
          {
            'value': '40',
            'text': 'Pool',
            'icon': ''
          },
          {
            'value': '41',
            'text': 'Pool 2',
            'icon': ''
          },
          {
            'value': '50',
            'text': 'Transfer',
            'icon': ''
          },
          {
            'value': '60',
            'text': 'Cooling',
            'icon': ''
          }
        ],
        """
        value_lookup = {
            "Off": HvacMode.Idle,
            "Hot water": HvacMode.Water,
            "Heating": HvacMode.Heat,
        }
        sensor = self.get_sensor(SensorType.HvacMode)
        ret = self._handle_sensor(sensor)
        if ret is not None:
            return value_lookup.get(ret, HvacMode.Unknown)
        return HvacMode.Unknown



    async def _get_operation_value(self, operation: HvacOperations, set_val: any = None):
        match operation:
            case HvacOperations.Offset:
                return self._cap_nibe_offset_value(set_val)
            case HvacOperations.VentBoost | HvacOperations.WaterBoost:
                return set_val
        raise ValueError(f"Operation {operation} not supported")

    def _service_domain_per_operation(self, operation: HvacOperations) -> str:
        match operation:
            case HvacOperations.Offset:
                return "input_number"
            case HvacOperations.VentBoost | HvacOperations.WaterBoost:
                return "switch"
        raise ValueError(f"Operation {operation} not supported")

    def _transform_servicecall_value(self, value: any, operation: HvacOperations) -> any:
        match operation:
            case HvacOperations.Offset:
                return value
            case HvacOperations.VentBoost | HvacOperations.WaterBoost:
                return "turn_on" if value == 1 else "turn_off"

    def _set_operation_call_parameters(self, operation: HvacOperations, _value: any) -> Tuple[str, dict, str]:
        call_operation = self._transform_servicecall_value(_value, operation)
        service_domain = self._service_domain_per_operation(operation)
        params = {
                #"option": self._transform_servicecall_value(_value, operation),
                "entity_id": self._servicecall_types()[operation]
            }

        return call_operation, params, service_domain

    @staticmethod
    def _cap_nibe_offset_value(val: int):
        """Nibe only supports offsets between -10 and 10"""
        if abs(val) <= NIBE_MAX_THRESHOLD:
            return val
        return NIBE_MAX_THRESHOLD if val > NIBE_MAX_THRESHOLD else NIBE_MIN_THRESHOLD
