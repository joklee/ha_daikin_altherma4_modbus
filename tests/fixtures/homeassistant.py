"""Pytest fixtures for Home Assistant mocking."""

from types import SimpleNamespace
from unittest.mock import Mock

import pytest


@pytest.fixture
def mock_hass():
    """Create a mock Home Assistant instance."""
    hass = Mock()
    hass.data = {}
    hass.config = Mock()
    hass.config.time_zone = "Europe/Berlin"
    return hass


@pytest.fixture
def mock_coordinator():
    """Create a mock coordinator with empty data."""
    coordinator = Mock()
    coordinator.data = {}
    return coordinator


@pytest.fixture
def mock_entry():
    """Create a mock config entry."""
    return SimpleNamespace(
        entry_id="test_entry",
        data={"host": "192.168.1.100", "port": 502},
        options={},
        state="loaded",
    )
