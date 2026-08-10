"""Pytest fixtures for Home Assistant mocks."""

from types import SimpleNamespace
from unittest.mock import Mock

import pytest


@pytest.fixture
def mock_hass():
    """Mock Home Assistant instance."""
    hass_mock = Mock()
    hass_mock.data = {}
    hass_mock.config = Mock()
    hass_mock.config.time_zone = "Europe/Berlin"
    return hass_mock


@pytest.fixture
def mock_entry():
    """Mock config entry."""
    entry = SimpleNamespace(
        entry_id="test_entry",
        data={"host": "192.168.1.100", "port": 502},
        options={},
        state="loaded",
    )
    return entry


@pytest.fixture
def mock_coordinator():
    """Create a mock coordinator with test data."""
    coordinator = Mock()
    coordinator.data = {}
    return coordinator
