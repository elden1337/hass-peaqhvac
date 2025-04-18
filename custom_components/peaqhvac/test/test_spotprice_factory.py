"""Test the SpotPriceFactory with GE-Spot support."""
import unittest
from unittest.mock import MagicMock, patch

import pytest

from custom_components.peaqhvac.const import PLATFORM_GESPOT
from custom_components.peaqhvac.service.spotprice.spotprice_factory import SpotPriceFactory


class TestSpotPriceFactory:
    """Test the SpotPriceFactory with GE-Spot support."""

    def test_create_with_gespot_entity(self):
        """Test creating a SpotPrice instance with a GE-Spot entity."""
        # Mock the hub
        hub = MagicMock()
        hub.state_machine.data = {
            "entity_registry": MagicMock()
        }
        
        # Mock the entity registry
        entity_registry = hub.state_machine.data["entity_registry"]
        entity_entry = MagicMock()
        entity_entry.platform = PLATFORM_GESPOT
        entity_registry.async_get.return_value = entity_entry
        
        # Mock the observer
        observer = MagicMock()
        
        # Mock the PeaqSystem
        PeaqSystem = MagicMock()
        PeaqSystem.PeaqHvac = MagicMock()
        
        # Mock the CoreSpotPriceFactory
        with patch("custom_components.peaqhvac.service.spotprice.spotprice_factory.CoreSpotPriceFactory") as mock_core_factory:
            mock_result = MagicMock()
            mock_core_factory.create_nordpool.return_value = mock_result
            
            # Call the function
            result = SpotPriceFactory.create(
                hub=hub,
                observer=observer,
                system=PeaqSystem.PeaqHvac,
                entity="sensor.ge_spot_current_price"
            )
            
            # Verify that create_nordpool was called with the correct arguments
            mock_core_factory.create_nordpool.assert_called_once_with(
                hub, observer, PeaqSystem.PeaqHvac, False, True, "sensor.ge_spot_current_price"
            )
            
            # Verify that the result is what we expect
            assert result == mock_result

    def test_create_with_gespot_entity_fallback(self):
        """Test creating a SpotPrice instance with a GE-Spot entity that needs fallback."""
        # Mock the hub
        hub = MagicMock()
        hub.state_machine.data = {
            "entity_registry": MagicMock()
        }
        
        # Mock the entity registry
        entity_registry = hub.state_machine.data["entity_registry"]
        entity_entry = MagicMock()
        entity_entry.platform = PLATFORM_GESPOT
        entity_registry.async_get.return_value = entity_entry
        
        # Mock the observer
        observer = MagicMock()
        
        # Mock the PeaqSystem
        PeaqSystem = MagicMock()
        PeaqSystem.PeaqHvac = MagicMock()
        
        # Mock the CoreSpotPriceFactory
        with patch("custom_components.peaqhvac.service.spotprice.spotprice_factory.CoreSpotPriceFactory") as mock_core_factory:
            # Make create_nordpool raise an exception to test the fallback
            mock_core_factory.create_nordpool.side_effect = Exception("Test exception")
            
            mock_result = MagicMock()
            mock_core_factory.create.return_value = mock_result
            
            # Call the function
            result = SpotPriceFactory.create(
                hub=hub,
                observer=observer,
                system=PeaqSystem.PeaqHvac,
                entity="sensor.ge_spot_current_price"
            )
            
            # Verify that create_nordpool was called with the correct arguments
            mock_core_factory.create_nordpool.assert_called_once_with(
                hub, observer, PeaqSystem.PeaqHvac, False, True, "sensor.ge_spot_current_price"
            )
            
            # Verify that create was called with the correct arguments as fallback
            mock_core_factory.create.assert_called_once_with(
                hub, observer, PeaqSystem.PeaqHvac, False, True, "sensor.ge_spot_current_price"
            )
            
            # Verify that the result is what we expect
            assert result == mock_result

    def test_create_with_non_gespot_entity(self):
        """Test creating a SpotPrice instance with a non-GE-Spot entity."""
        # Mock the hub
        hub = MagicMock()
        hub.state_machine.data = {
            "entity_registry": MagicMock()
        }
        
        # Mock the entity registry
        entity_registry = hub.state_machine.data["entity_registry"]
        entity_entry = MagicMock()
        entity_entry.platform = "nordpool"  # Not GE-Spot
        entity_registry.async_get.return_value = entity_entry
        
        # Mock the observer
        observer = MagicMock()
        
        # Mock the PeaqSystem
        PeaqSystem = MagicMock()
        PeaqSystem.PeaqHvac = MagicMock()
        
        # Mock the CoreSpotPriceFactory
        with patch("custom_components.peaqhvac.service.spotprice.spotprice_factory.CoreSpotPriceFactory") as mock_core_factory:
            mock_result = MagicMock()
            mock_core_factory.create.return_value = mock_result
            
            # Call the function
            result = SpotPriceFactory.create(
                hub=hub,
                observer=observer,
                system=PeaqSystem.PeaqHvac,
                entity="sensor.nordpool_current_price"
            )
            
            # Verify that create was called with the correct arguments
            mock_core_factory.create.assert_called_once_with(
                hub, observer, PeaqSystem.PeaqHvac, False, True, "sensor.nordpool_current_price"
            )
            
            # Verify that the result is what we expect
            assert result == mock_result

    def test_create_with_no_entity(self):
        """Test creating a SpotPrice instance with no entity."""
        # Mock the hub
        hub = MagicMock()
        hub.state_machine.data = {
            "entity_registry": MagicMock()
        }
        
        # Mock the observer
        observer = MagicMock()
        
        # Mock the PeaqSystem
        PeaqSystem = MagicMock()
        PeaqSystem.PeaqHvac = MagicMock()
        
        # Mock the CoreSpotPriceFactory
        with patch("custom_components.peaqhvac.service.spotprice.spotprice_factory.CoreSpotPriceFactory") as mock_core_factory:
            mock_result = MagicMock()
            mock_core_factory.create.return_value = mock_result
            
            # Call the function
            result = SpotPriceFactory.create(
                hub=hub,
                observer=observer,
                system=PeaqSystem.PeaqHvac,
                entity=None
            )
            
            # Verify that create was called with the correct arguments
            mock_core_factory.create.assert_called_once_with(
                hub, observer, PeaqSystem.PeaqHvac, False, True, None
            )
            
            # Verify that the result is what we expect
            assert result == mock_result
