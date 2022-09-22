import logging

from custom_components.peaqhvac.service.hvac.ihvac import IHvac
from custom_components.peaqhvac.service.models.hvacoperations import HvacOperations
from custom_components.peaqhvac.service.models.sensortypes import SensorType

_LOGGER = logging.getLogger(__name__)


class Nibe(IHvac):
    domain = "Nibe"
    calltypes = {
        HvacOperations.Offset: 47011,
        HvacOperations.VentBoost: "HotWaterBoost",
        HvacOperations.WaterBoost: "VentilationBoost"
    }

    """
    make function that returns nodemand for heating if degree-minutes are > 0
    degree minutes: sensor.nibe_{systemid}_43005
    """

    def get_sensor(self, sensor: SensorType) -> str:
        types = {
            SensorType.DegreeMinutes: f"sensor.nibe_{self._hub.options.systemid}_43005",
            SensorType.WaterTemp: f"states.water_heater.nibe_{self._hub.options.systemid}_40014_47387|current_temperature"
        }
        return types[sensor]

    @property
    def hvac_offset(self) -> int:
        sensor = f"climate.nibe_{self._hub.options.systemid}_s1_supply"
        ret = self._hass.states.get(sensor)
        if ret is not None:
            try:
                ret_attr = ret.attributes.get("offset_heat")
                return int(ret_attr)
            except Exception as e:
                _LOGGER.exception(e)
        return 0

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
                "parameter": self.calltypes[operation],
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

