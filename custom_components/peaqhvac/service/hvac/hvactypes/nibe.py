import logging

from custom_components.peaqhvac.service.hvac.ihvac import IHvac
from custom_components.peaqhvac.service.models.hvacmode import HvacMode
from custom_components.peaqhvac.service.models.hvacoperations import HvacOperations
from custom_components.peaqhvac.service.models.sensortypes import SensorType

_LOGGER = logging.getLogger(__name__)


class Nibe(IHvac):
    domain = "Nibe"
    listenerentities = []

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

    def _get_sensors_for_callback(self, types:dict) -> list:
        ret = []
        for t in types:
            item = types[t]
            ret.append(item.split('|')[0])
        self.listenerentities = ret
        return ret

    @property
    def hvac_offset(self) -> int:
        sensor = self.get_sensor(SensorType.Offset)
        ret = self._handle_sensor(sensor)
        if ret is not None:
            return int(ret)
        else:
            _LOGGER.debug("could not get offset from hvac")
        return 0

    @property
    def hvac_dm(self) -> int:
        sensor = self.get_sensor(SensorType.DegreeMinutes)
        ret = self._handle_sensor(sensor)
        if ret is not None:
            return int(float(ret))
        else:
            _LOGGER.debug("could not get DM from hvac")
        return 0

    @property
    def hvac_compressor_start(self) -> int:
        sensor = self.get_sensor(SensorType.DMCompressorStart)
        ret = self._handle_sensor(sensor)
        if ret is not None:
            return int(ret)
        else:
            _LOGGER.debug("could not get compressor_start from hvac")
        return 0

    @property
    def hvac_watertemp(self) -> float:
        sensor = self.get_sensor(SensorType.WaterTemp)
        ret = self._handle_sensor(sensor)
        if ret is not None:
            return float(ret)
        else:
            _LOGGER.debug("could not get water temp from hvac")
        return 0.0

    @property
    def hvac_mode(self) -> HvacMode:
        sensor = self.get_sensor(SensorType.HvacMode)
        ret = self._handle_sensor(sensor)
        if ret is not None:
            if ret == "heating":
                return HvacMode.Heat
            elif ret == "idle":
                return HvacMode.Idle
        else:
            _LOGGER.debug("could not get hvac mode from hvac")
        return HvacMode.Unknown


    _servicecall_types = {
        HvacOperations.Offset:     47011,
        HvacOperations.VentBoost:  "HotWaterBoost",
        HvacOperations.WaterBoost: "VentilationBoost"
    }

    async def update_system(self, operation: HvacOperations):
        _should_call = False
        
        if self.hub.sensors.peaq_enabled.value is True:
            _LOGGER.debug("Requesting to update hvac-offset")
            _value = self.current_offset if operation is HvacOperations.Offset else 1 # todo: fix this later. must be more fluid.
            match operation:
                case HvacOperations.Offset:
                    _value = await self._set_offset_value(_value)
                    _should_call = self.hub.sensors.average_temp_outdoors.initialized_percentage > 0.5
                case _:
                    pass
            params = {
                "system": int(self.hub.options.systemid),
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

