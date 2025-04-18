"""Custom SpotPriceFactory with GE-Spot support."""
import logging
from typing import Optional

from peaqevcore.common.models.peaq_system import PeaqSystem
from peaqevcore.common.spotprice.spotprice_base import SpotPriceBase
from peaqevcore.common.spotprice.spotprice_factory import SpotPriceFactory as CoreSpotPriceFactory

from custom_components.peaqhvac.const import PLATFORM_GESPOT

_LOGGER = logging.getLogger(__name__)


class SpotPriceFactory:
    """Factory for creating SpotPrice instances with GE-Spot support."""

    @staticmethod
    def create(
        hub,
        observer,
        system: PeaqSystem,
        test: bool = False,
        is_active: bool = True,
        entity: Optional[str] = None
    ) -> SpotPriceBase:
        """Create a SpotPrice instance with GE-Spot support.
        
        This factory extends the core SpotPriceFactory to add support for GE-Spot entities.
        If the entity is a GE-Spot entity, it uses the Nordpool implementation since
        GE-Spot has the same data format. For other entity types, it falls back to the
        core implementation.
        
        Args:
            hub: The hub instance
            observer: The observer instance
            system: The PeaqSystem instance
            test: Whether this is a test instance
            is_active: Whether the instance is active
            entity: The entity ID of the price sensor
            
        Returns:
            A SpotPriceBase instance
        """
        # Check if entity is provided and if it's a GE-Spot entity
        if entity is not None:
            entity_registry = hub.state_machine.data["entity_registry"]
            entity_entry = entity_registry.async_get(entity)
            
            if entity_entry is not None and entity_entry.platform == PLATFORM_GESPOT:
                _LOGGER.debug("Creating GE-Spot SpotPrice instance")
                
                # Use the same implementation as Nordpool since GE-Spot has the same data format
                # by default, but handle different possible data formats
                try:
                    # First try with Nordpool implementation
                    return CoreSpotPriceFactory.create_nordpool(
                        hub, observer, system, test, is_active, entity
                    )
                except Exception as e:
                    _LOGGER.warning(f"Failed to create GE-Spot SpotPrice instance with Nordpool implementation: {e}")
                    # Fall back to the core implementation
                    _LOGGER.debug("Falling back to core implementation for GE-Spot entity")
                    return CoreSpotPriceFactory.create(
                        hub, observer, system, test, is_active, entity
                    )

        # Fall back to the core implementation for other entity types
        return CoreSpotPriceFactory.create(
            hub, observer, system, test, is_active, entity
        )
