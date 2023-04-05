import logging

from custom_components.peaqhvac.service.hvac.ihvac import IHvac
from custom_components.peaqhvac.service.models.enums.hvacoperations import \
    HvacOperations

_LOGGER = logging.getLogger(__name__)


class Thermia(IHvac):
    async def update_system(self, operation: HvacOperations):
        pass
