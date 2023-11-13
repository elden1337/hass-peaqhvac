from __future__ import annotations

from typing import TYPE_CHECKING

from peaqevcore.services.hourselection.hoursselection import Hoursselection

from custom_components.peaqhvac.service.hvac.offset.offset_coordinator_peaqev import OffsetCoordinatorPeaqEv
from custom_components.peaqhvac.service.hvac.offset.offset_coordinator_standalone import OffsetCoordinatorStandAlone

if TYPE_CHECKING:
    from custom_components.peaqhvac.service.hub.hub import Hub
from custom_components.peaqhvac.service.hvac.offset.offset_coordinator import OffsetCoordinator


class OffsetFactory:

    @staticmethod
    def create(hub: Hub) -> OffsetCoordinator:
        if hub.peaqev_discovered:
            return OffsetCoordinatorPeaqEv(hub, None)
        return OffsetCoordinatorStandAlone(hub, Hoursselection())

