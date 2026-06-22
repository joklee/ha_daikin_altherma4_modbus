"""Pytest configuration for ha_daikin_altherma4_modbus tests."""

import sys
import types
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Setup homeassistant stubs BEFORE any imports
if "homeassistant" not in sys.modules:
    homeassistant = types.ModuleType("homeassistant")
    homeassistant.__path__ = []
    sys.modules["homeassistant"] = homeassistant

    const_module = types.ModuleType("homeassistant.const")
    const_module.EntityCategory = types.SimpleNamespace(DIAGNOSTIC="diagnostic")
    sys.modules["homeassistant.const"] = const_module

    core_module = types.ModuleType("homeassistant.core")
    core_module.Event = object
    core_module.HomeAssistant = object
    sys.modules["homeassistant.core"] = core_module

    helpers_module = types.ModuleType("homeassistant.helpers")
    helpers_module.__path__ = []
    sys.modules["homeassistant.helpers"] = helpers_module

    update_coordinator_module = types.ModuleType(
        "homeassistant.helpers.update_coordinator"
    )
    # Use type() for all stubs to avoid metaclass conflicts
    MockCoordinatorEntity = type(
        "MockCoordinatorEntity",
        (),
        {"__init__": lambda self, coordinator=None: setattr(self, "coordinator", coordinator)},
    )
    MockDataUpdateCoordinator = type(
        "MockDataUpdateCoordinator",
        (),
        {"__init__": lambda self, hass=None, logger=None, name=None, update_interval=None: (setattr(self, "hass", hass), setattr(self, "data", {}))},
    )
    MockCoordinatorEntity.__module__ = "homeassistant.helpers.update_coordinator"
    MockDataUpdateCoordinator.__module__ = "homeassistant.helpers.update_coordinator"

    update_coordinator_module.DataUpdateCoordinator = MockDataUpdateCoordinator
    update_coordinator_module.CoordinatorEntity = MockCoordinatorEntity
    update_coordinator_module.UpdateFailed = Exception
    sys.modules["homeassistant.helpers.update_coordinator"] = update_coordinator_module

    helpers_typing_module = types.ModuleType("homeassistant.helpers.typing")
    helpers_typing_module.ConfigType = dict
    sys.modules["homeassistant.helpers.typing"] = helpers_typing_module

    # Exceptions stub
    exceptions_module = types.ModuleType("homeassistant.exceptions")
    exceptions_module.ConfigEntryNotReady = type(
        "ConfigEntryNotReady", (Exception,), {}
    )
    exceptions_module.HomeAssistantError = type("HomeAssistantError", (Exception,), {})
    exceptions_module.ServiceValidationError = type(
        "ServiceValidationError", (Exception,), {}
    )
    sys.modules["homeassistant.exceptions"] = exceptions_module

    # Issue registry stub for repair issues
    issue_registry_module = types.ModuleType("homeassistant.helpers.issue_registry")
    issue_registry_module.IssueSeverity = types.SimpleNamespace(
        ERROR="error", WARNING="warning"
    )
    issue_registry_module.async_create_issue = lambda *a, **kw: None
    issue_registry_module.async_delete_issue = lambda *a, **kw: None
    issue_registry_module.async_get = lambda hass: types.SimpleNamespace(issues={})
    sys.modules["homeassistant.helpers.issue_registry"] = issue_registry_module

    # All entity stubs use type() to avoid metaclass conflicts
    def _make_entity(name):
        """Create a base entity class using type() for consistent metaclass."""
        return type(name, (), {"__init__": lambda self, **kwargs: None})

    # Restore state stub
    restore_state_module = types.ModuleType("homeassistant.helpers.restore_state")
    restore_state_module.RestoreEntity = _make_entity("RestoreEntity")
    sys.modules["homeassistant.helpers.restore_state"] = restore_state_module

    # Binary sensor stub
    binary_sensor_module = types.ModuleType("homeassistant.components.binary_sensor")
    binary_sensor_module.BinarySensorEntity = _make_entity("BinarySensorEntity")
    sys.modules["homeassistant.components.binary_sensor"] = binary_sensor_module

    # Sensor stub
    sensor_module = types.ModuleType("homeassistant.components.sensor")
    sensor_module.SensorEntity = _make_entity("SensorEntity")
    sensor_module.SensorStateClass = types.SimpleNamespace(MEASUREMENT="measurement")
    sys.modules["homeassistant.components.sensor"] = sensor_module

    # Switch stub
    switch_module = types.ModuleType("homeassistant.components.switch")
    switch_module.SwitchEntity = _make_entity("SwitchEntity")
    sys.modules["homeassistant.components.switch"] = switch_module

    # Number stub
    number_module = types.ModuleType("homeassistant.components.number")
    number_module.NumberEntity = _make_entity("NumberEntity")
    sys.modules["homeassistant.components.number"] = number_module

    # Select stub
    select_module = types.ModuleType("homeassistant.components.select")
    select_module.SelectEntity = _make_entity("SelectEntity")
    sys.modules["homeassistant.components.select"] = select_module

    # Climate stub
    climate_module = types.ModuleType("homeassistant.components.climate")
    climate_module.ClimateEntity = _make_entity("ClimateEntity")
    climate_const_module = types.ModuleType("homeassistant.components.climate.const")
    climate_const_module.ClimateEntityFeature = types.SimpleNamespace(
        TARGET_TEMPERATURE=1, FAN_MODE=2
    )
    climate_const_module.HVACAction = types.SimpleNamespace(
        HEATING="heating", COOLING="cooling", IDLE="idle", OFF="off"
    )
    climate_const_module.HVACMode = types.SimpleNamespace(
        HEAT="heat", COOL="cool", AUTO="auto", OFF="off"
    )
    sys.modules["homeassistant.components.climate"] = climate_module
    sys.modules["homeassistant.components.climate.const"] = climate_const_module

    # Unit of temperature stub
    const_module.UnitOfTemperature = types.SimpleNamespace(CELSIUS="°C")
