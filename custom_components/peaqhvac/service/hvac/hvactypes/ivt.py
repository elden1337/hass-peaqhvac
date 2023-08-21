import logging

from custom_components.peaqhvac.service.hvac.interfaces.ihvac import IHvac
from custom_components.peaqhvac.service.models.enums.hvacoperations import \
    HvacOperations

_LOGGER = logging.getLogger(__name__)


class IVT(IHvac):
    async def update_system(self, operation: HvacOperations):
        pass
