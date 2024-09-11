import logging
from typing import Tuple

from custom_components.peaqhvac.service.hvac.interfaces.ihvactype import IHvacType
from custom_components.peaqhvac.service.models.enums.hvacmode import HvacMode
from custom_components.peaqhvac.service.models.enums.hvacoperations import \
    HvacOperations
from custom_components.peaqhvac.service.models.enums.sensortypes import SensorType

_LOGGER = logging.getLogger(__name__)


class IVT(IHvacType):
    async def update_system(self, operation: HvacOperations):
        pass

    @property
    def delta_return_temp(self):
        pass

    @property
    def fan_speed(self) -> float:
        pass

    @property
    def hvac_mode(self) -> HvacMode:
        pass

    def get_sensor(self, sensor: SensorType = None):
        pass

    def _set_operation_call_parameters(
            self, operation: HvacOperations, _value: any
    ) -> Tuple[str, dict, str]:
        pass
