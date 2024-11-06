import logging

from custom_components.peaqhvac.service.hvac.hvactypes.hvactype import HvacType
from custom_components.peaqhvac.service.models.enums.hvacoperations import \
    HvacOperations

_LOGGER = logging.getLogger(__name__)


class Thermia(HvacType):
    async def update_system(self, operation: HvacOperations):
        pass
