#!/usr/bin/env python3
"""
Shared test utilities for Daikin Altherma 4 Modbus integration tests.
"""

import sys
import types
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock


class MockConst:
    """Mock Home Assistant constants."""

    EntityCategory = Mock()
    EntityCategory.DIAGNOSTIC = "diagnostic"
    UnitOfTemperature = "°C"


class MockDataUpdateCoordinator:
    """Mock DataUpdateCoordinator for testing."""

    def __init__(self, hass, logger, name, update_interval):
        self.hass = hass
        self.logger = logger
        self.name = name
        self.update_interval = update_interval
        self.data = {}

    async def async_config_entry_first_refresh(self):
        """Mock initial refresh used during integration setup."""
        return None


class UpdateFailed(Exception):
    """Mock UpdateFailed exception."""

    pass


class MockSensorEntity:
    """Mock SensorEntity for testing."""

    def __init__(self):
        self._attr_device_class = None
        self._attr_state_class = None
        self._attr_unique_id = None
        self._attr_native_unit_of_measurement = None
        self._attr_last_reset = None
        self._attr_last_reported = None


def setup_home_assistant_mocks():
    """Set up all Home Assistant module mocks."""
    # Install mocks
    sys.modules["homeassistant"] = Mock()
    sys.modules["homeassistant.const"] = MockConst()
    sys.modules["homeassistant.core"] = Mock()
    sys.modules["homeassistant.helpers"] = Mock()
    sys.modules["homeassistant.helpers.typing"] = Mock()
    sys.modules["homeassistant.helpers.typing"].ConfigType = Mock()
    sys.modules["homeassistant.helpers.update_coordinator"] = Mock()
    sys.modules[
        "homeassistant.helpers.update_coordinator"
    ].data_update_coordinator = MockDataUpdateCoordinator
    sys.modules["homeassistant.helpers.update_coordinator"].UpdateFailed = UpdateFailed
    sys.modules["homeassistant.components"] = Mock()
    sys.modules["homeassistant.components.sensor"] = Mock()
    sys.modules["homeassistant.components.sensor"].SensorEntity = MockSensorEntity


def setup_project_paths():
    """Set up project paths for testing."""
    project_root = Path(__file__).parent.parent
    sys.path.insert(0, str(project_root))
    return project_root


def load_const_module(project_root):
    """Load the const module for testing."""
    custom_components_path = (
        project_root / "custom_components" / "ha_daikin_altherma4_modbus"
    )

    # Load const first
    with open(custom_components_path / "const.py", "r") as f:
        source = f.read()
    const_module = types.ModuleType("const_module")
    exec(source, const_module.__dict__)

    return const_module


def create_mock_coordinator():
    """Create a mock coordinator with test data."""
    coordinator = Mock()
    coordinator.data = {}
    return coordinator


def create_test_trigger_time():
    """Create a consistent test trigger time."""
    return datetime(2024, 3, 2, 20, 30, 0)
