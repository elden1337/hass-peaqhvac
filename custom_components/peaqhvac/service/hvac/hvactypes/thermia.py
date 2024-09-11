import logging

from custom_components.peaqhvac.service.hvac.interfaces.ihvactype import IHvacType
from custom_components.peaqhvac.service.models.enums.hvacoperations import \
    HvacOperations

_LOGGER = logging.getLogger(__name__)


class Thermia(IHvacType):
    async def update_system(self, operation: HvacOperations):
        pass
