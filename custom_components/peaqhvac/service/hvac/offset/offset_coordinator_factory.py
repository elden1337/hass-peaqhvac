from __future__ import annotations

from typing import TYPE_CHECKING

from peaqevcore.services.hourselection.hoursselection import Hoursselection

from custom_components.peaqhvac.service.hvac.offset.offset_coordinator_peaqev import (
    OffsetCoordinatorPeaqEv,
)
from custom_components.peaqhvac.service.hvac.offset.offset_coordinator_standalone import (
    OffsetCoordinatorStandAlone,
)
from custom_components.peaqhvac.service.observer.iobserver_coordinator import IObserver

if TYPE_CHECKING:
    from custom_components.peaqhvac.service.hub.hub import Hub
from custom_components.peaqhvac.service.hvac.offset.offset_coordinator import (
    OffsetCoordinator,
)


class OffsetFactory:

    @staticmethod
    def create(hub: Hub, observer: IObserver) -> OffsetCoordinator:
        if hub.options.misc_options.peaqev_discovered:
            return OffsetCoordinatorPeaqEv(hub, observer, None)
        return OffsetCoordinatorStandAlone(hub, observer, Hoursselection())
