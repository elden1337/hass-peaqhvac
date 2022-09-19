import logging

from custom_components.peaqhvac.service.hvac.ihvac import IHvac
from custom_components.peaqhvac.service.models.hvacoperations import HvacOperations

_LOGGER = logging.getLogger(__name__)


class Nibe(IHvac):
    domain = "Nibe"
    calltypes = {
        HvacOperations.Offset: 47011,
        HvacOperations.VentBoost: "HotWaterBoost",
        HvacOperations.WaterBoost: "VentilationBoost"
    }

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
        _LOGGER.debug("Requesting to update hvac-offset")
        _value = self.current_offset if operation is HvacOperations.Offset else 1 # todo: fix this later. must be more fluid.
        params = {
            "system": int(self._hub.options.systemid),
            "parameter": self.calltypes[operation],
            "value": _value
        }

        await self._hass.services.async_call(
            self.domain,
            "set_parameter",
            params
        )
        _LOGGER.debug(f"Calling hvac-system with {operation} and {_value}")