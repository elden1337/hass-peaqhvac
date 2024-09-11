from __future__ import annotations

import logging

from peaqevcore.common.models.observer_types import ObserverTypes
from peaqevcore.services.hourselection.hoursselection import Hoursselection

from custom_components.peaqhvac.service.hvac.offset.offset_coordinator import OffsetCoordinator
from custom_components.peaqhvac.service.observer.iobserver_coordinator import IObserver


_LOGGER = logging.getLogger(__name__)

class OffsetCoordinatorStandAlone(OffsetCoordinator):
    """The class that provides the offsets for the hvac with peaqev installed"""

    def __init__(self, hub, observer: IObserver, hours_type: Hoursselection = None):  # type: ignore
        _LOGGER.debug("initializing an hourselection-instance")
        observer.add(ObserverTypes.PricesChanged, self.async_update_prices)
        observer.add(ObserverTypes.SpotpriceInitialized, self.async_update_prices)
        super().__init__(hub, observer, hours_type)

    @property
    def prices(self) -> list:
        return self.hours.prices

    @property
    def prices_tomorrow(self) -> list:
        return self.hours.prices_tomorrow

    @property
    def min_price(self) -> float:
        return 0

    async def async_update_prices(self, prices) -> None:
        await self.hours.async_update_prices(prices[0], prices[1])
        _LOGGER.debug(f"Updated prices to {self.hours.prices, self.hours.prices_tomorrow}")
        self._set_offset()
        self._update_model()
