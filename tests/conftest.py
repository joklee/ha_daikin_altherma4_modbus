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
    const_module.CONF_HOST = "host"
    const_module.CONF_PORT = "port"
    const_module.UnitOfTemperature = types.SimpleNamespace(CELSIUS="°C")
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

    # Single base class for all entity stubs to avoid metaclass conflicts
    class _EntityBase:
        def __init__(self, **kwargs):
            pass

    # Restore state stub
    restore_state_module = types.ModuleType("homeassistant.helpers.restore_state")
    restore_state_module.RestoreEntity = _EntityBase
    sys.modules["homeassistant.helpers.restore_state"] = restore_state_module

    # Binary sensor stub
    binary_sensor_module = types.ModuleType("homeassistant.components.binary_sensor")
    binary_sensor_module.BinarySensorEntity = _EntityBase
    sys.modules["homeassistant.components.binary_sensor"] = binary_sensor_module

    # Sensor stub
    sensor_module = types.ModuleType("homeassistant.components.sensor")
    sensor_module.SensorEntity = _EntityBase
    sensor_module.SensorStateClass = types.SimpleNamespace(MEASUREMENT="measurement")
    sys.modules["homeassistant.components.sensor"] = sensor_module

    # Switch stub
    switch_module = types.ModuleType("homeassistant.components.switch")
    switch_module.SwitchEntity = _EntityBase
    sys.modules["homeassistant.components.switch"] = switch_module

    # Number stub
    number_module = types.ModuleType("homeassistant.components.number")
    number_module.NumberEntity = _EntityBase
    sys.modules["homeassistant.components.number"] = number_module

    # Select stub
    select_module = types.ModuleType("homeassistant.components.select")
    select_module.SelectEntity = _EntityBase
    sys.modules["homeassistant.components.select"] = select_module

    # Climate stub
    climate_module = types.ModuleType("homeassistant.components.climate")
    climate_module.ClimateEntity = _EntityBase
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

    # Config entries stub
    config_entries_module = types.ModuleType("homeassistant.config_entries")
    class MockConfigFlow:
        def async_abort(self, reason=None):
            return {"reason": reason}
        def async_show_form(self, **kwargs):
            return kwargs
    config_entries_module.ConfigFlow = MockConfigFlow
    config_entries_module.ConfigEntry = type("ConfigEntry", (), {})
    sys.modules["homeassistant.config_entries"] = config_entries_module

    # Components diagnostics stub
    diagnostics_module = types.ModuleType("homeassistant.components.diagnostics")
    diagnostics_module.async_redact_data = lambda data, to_redact: {
        k: "**REDACTED**" if k in to_redact else v for k, v in data.items()
    }
    sys.modules["homeassistant.components.diagnostics"] = diagnostics_module

    # Unit of temperature stub
    const_module.UnitOfTemperature = types.SimpleNamespace(CELSIUS="°C")
