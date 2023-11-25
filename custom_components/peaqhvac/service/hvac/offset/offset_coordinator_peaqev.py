from __future__ import annotations

import logging
from peaqevcore.services.hourselection.hoursselection import Hoursselection
from custom_components.peaqhvac.service.hvac.offset.offset_coordinator import OffsetCoordinator

_LOGGER = logging.getLogger(__name__)

class OffsetCoordinatorPeaqEv(OffsetCoordinator):
    """The class that provides the offsets for the hvac with peaqev installed"""

    def __init__(self, hub, hours_type: Hoursselection = None): #type: ignore
        _LOGGER.debug("found peaqev and will not init hourselection")
        self._prices = None
        self._prices_tomorrow = None
        super().__init__(hub, hours_type)

    @property
    def prices(self) -> list:
        return self._prices

    @property
    def prices_tomorrow(self) -> list:
        return self._prices_tomorrow

    @property
    def min_price(self) -> float:
        try:
            return self._hub.sensors.peaqev_facade.min_price
        except:
            return 0

    async def async_update_prices(self, prices) -> None:
        if self._prices != prices[0]:
            self._prices = prices[0]
        if self._prices_tomorrow != prices[1]:
            self._prices_tomorrow = prices[1]
        self._set_offset()
        self._update_model()