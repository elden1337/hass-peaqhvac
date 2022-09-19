import logging
from custom_components.peaqhvac.service.models.hvacoperations import HvacOperations
from custom_components.peaqhvac.service.hvac.ihvac import IHvac
_LOGGER = logging.getLogger(__name__)


class IVT(IHvac):
    async def update_system(self, operation: HvacOperations):
        pass