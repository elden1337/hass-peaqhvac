from __future__ import annotations

import logging
from peaqevcore.services.hourselection.hoursselection import Hoursselection
from custom_components.peaqhvac.service.hvac.offset.offset_coordinator import OffsetCoordinator

_LOGGER = logging.getLogger(__name__)

class OffsetCoordinatorPeaqEv(OffsetCoordinator):
    """The class that provides the offsets for the hvac with peaqev installed"""

    def __init__(self, hub, hours_type: Hoursselection = None): #type: ignore
        _LOGGER.debug("found peaqev and will not init hourselection")
        super().__init__(hub, hours_type)

    @property
    def prices(self) -> list:
        return self._prices

    @property
    def prices_tomorrow(self) -> list:
        return self._prices_tomorrow

    @property
    def offsets(self) -> dict:
        ret = self._hub.sensors.peaqev_facade.offsets
        if len(ret) == 0 or not ret:
            _LOGGER.warning("Tried to get offsets from peaqev, but got nothing")
        return ret

    async def async_update_prices(self, prices) -> None:
        if self._prices != prices[0]:
            self._prices = prices[0]
        if self._prices_tomorrow != prices[1]:
            self._prices_tomorrow = prices[1]
        self._set_offset()
        self._update_model()