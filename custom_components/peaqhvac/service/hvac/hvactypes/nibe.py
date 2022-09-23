import logging

from custom_components.peaqhvac.service.hvac.ihvac import IHvac
from custom_components.peaqhvac.service.models.hvacoperations import HvacOperations
from custom_components.peaqhvac.service.models.sensortypes import SensorType

_LOGGER = logging.getLogger(__name__)


class Nibe(IHvac):
    domain = "Nibe"

    def get_sensor(self, getsensor: SensorType) -> str:
        types = {
            SensorType.Offset: f"climate.nibe_{self._hub.options.systemid}_s1_supply|offset_heat",
            SensorType.DegreeMinutes: f"sensor.nibe_{self._hub.options.systemid}_43005",
            SensorType.WaterTemp: f"states.water_heater.nibe_{self._hub.options.systemid}_40014_47387|current_temperature"
        }
        return types[getsensor]

    @property
    def hvac_offset(self) -> int:
        sensor = self.get_sensor(SensorType.Offset)
        ret = self._handle_sensor(sensor)
        if ret is not None:
            return int(ret)
        return 0

    @property
    def hvac_dm(self) -> int:
        sensor = self.get_sensor(SensorType.DegreeMinutes)
        ret = self._handle_sensor(sensor)
        if ret is not None:
            return int(ret)
        return 0

    @property
    def hvac_watertemp(self) -> float:
        sensor = self.get_sensor(SensorType.WaterTemp)
        ret = self._handle_sensor(sensor)
        if ret is not None:
            return float(ret)
        return 0.0

    def _handle_sensor(self, sensor:str):
        sensorobj = sensor.split('|')
        if len(sensorobj) == 1:
            return self._handle_sensor_basic(sensor)
        elif len(sensorobj) == 2:
            return self._handle_sensor_attribute(sensorobj)
        raise ValueError

    def _handle_sensor_basic(self, sensor:str):
        ret = self._hass.states.get(sensor)
        if ret is not None:
            return ret.state
        return None

    def _handle_sensor_attribute(self, sensorobj):
        ret = self._hass.states.get(sensorobj[0])
        if ret is not None:
            try:
                ret_attr = ret.attributes.get(sensorobj[1])
                return ret_attr
            except Exception as e:
                _LOGGER.exception(e)
        return 0

    _servicecall_types = {
        HvacOperations.Offset:     47011,
        HvacOperations.VentBoost:  "HotWaterBoost",
        HvacOperations.WaterBoost: "VentilationBoost"
    }

    async def update_system(self, operation: HvacOperations):
        _should_call = False
        
        if self._hub.sensors.peaq_enabled.value is True:
            _LOGGER.debug("Requesting to update hvac-offset")
            _value = self.current_offset if operation is HvacOperations.Offset else 1 # todo: fix this later. must be more fluid.
            match operation:
                case HvacOperations.Offset:
                    _value = await self._set_offset_value(_value)
                    _should_call = self._hub.sensors.average_temp_outdoors.initialized_percentage > 0.5
                case _:
                    pass
            params = {
                "system": int(self._hub.options.systemid),
                "parameter": self._servicecall_types[operation],
                "value": _value
            }
            if _should_call:
                await self._hass.services.async_call(
                    self.domain,
                    "set_parameter",
                    params
                )

    async def _set_offset_value(self, val: int):
        if abs(val) <= 10:
            return val
        return 10 if val > 10 else -10

