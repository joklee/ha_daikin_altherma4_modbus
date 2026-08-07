"""Pytest configuration for ha_daikin_altherma4_modbus tests."""

import abc
import sys
import types
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Setup homeassistant stubs BEFORE any imports
# Use a fake module with __path__ = [] to prevent Python from finding
# the real homeassistant package and its submodules
homeassistant = types.ModuleType("homeassistant")
homeassistant.__path__ = []
sys.modules["homeassistant"] = homeassistant

const_module = types.ModuleType("homeassistant.const")
const_module.EntityCategory = types.SimpleNamespace(DIAGNOSTIC="diagnostic")
const_module.CONF_HOST = "host"
const_module.CONF_PORT = "port"
const_module.UnitOfTemperature = types.SimpleNamespace(CELSIUS="°C")
sys.modules["homeassistant.const"] = const_module
homeassistant.const = const_module

# Create entity base class with ABCMeta to avoid metaclass conflicts
# when using multiple inheritance (e.g. CoordinatorEntity + BinarySensorEntity)
_HAMetaclass = abc.ABCMeta


class _HAEntityBase(metaclass=_HAMetaclass):
    def __init__(self, coordinator=None, **kwargs):
        self.coordinator = coordinator


class _CoordinatorEntity(_HAEntityBase):
    pass


class _BinarySensorEntity(_HAEntityBase):
    pass


class _SensorEntity(_HAEntityBase):
    pass


class _SwitchEntity(_HAEntityBase):
    pass


class _NumberEntity(_HAEntityBase):
    pass


class _SelectEntity(_HAEntityBase):
    pass


class _ClimateEntity(_HAEntityBase):
    pass


class _HADataUpdateCoordinator:
    def __init__(self, hass=None, logger=None, name=None, update_interval=None):
        self.hass = hass
        self.data = {}


class _ServiceCall:
    def __init__(self, domain=None, service=None, data=None):
        self.domain = domain
        self.service = service
        self.data = data or {}


_HAEntityBase.__module__ = "homeassistant.helpers.update_coordinator"
_HADataUpdateCoordinator.__module__ = "homeassistant.helpers.update_coordinator"

core_module = types.ModuleType("homeassistant.core")
core_module.Event = object
core_module.HomeAssistant = object
core_module.ServiceCall = _ServiceCall
sys.modules["homeassistant.core"] = core_module
homeassistant.core = core_module

helpers_module = types.ModuleType("homeassistant.helpers")
helpers_module.__path__ = []
sys.modules["homeassistant.helpers"] = helpers_module
homeassistant.helpers = helpers_module

# homeassistant.helpers.update_coordinator stub
update_coordinator_module = types.ModuleType("homeassistant.helpers.update_coordinator")
update_coordinator_module.DataUpdateCoordinator = _HADataUpdateCoordinator
update_coordinator_module.CoordinatorEntity = _CoordinatorEntity
update_coordinator_module.UpdateFailed = Exception
sys.modules["homeassistant.helpers.update_coordinator"] = update_coordinator_module
helpers_module.update_coordinator = update_coordinator_module

# homeassistant.helpers.typing stub
helpers_typing_module = types.ModuleType("homeassistant.helpers.typing")
helpers_typing_module.ConfigType = dict
sys.modules["homeassistant.helpers.typing"] = helpers_typing_module

# homeassistant.helpers.config_validation stub
# Must be attribute of helpers_module since code does: from homeassistant.helpers import config_validation as cv
cv_module = types.ModuleType("homeassistant.helpers.config_validation")
cv_module.string = lambda x: x
cv_module.boolean = bool
sys.modules["homeassistant.helpers.config_validation"] = cv_module
helpers_module.config_validation = cv_module

# homeassistant.helpers.service stub


class _ServiceValidationError(Exception):
    """Mock ServiceValidationError that accepts keyword arguments."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args)
        self.translation_domain = kwargs.get("translation_domain")
        self.translation_key = kwargs.get("translation_key")
        self.translation_placeholders = kwargs.get("translation_placeholders")


helpers_service_module = types.ModuleType("homeassistant.helpers.service")
helpers_service_module.ServiceCall = _ServiceCall
helpers_service_module.ServiceValidationError = _ServiceValidationError


def _async_register_admin_service(hass, domain, service, func, schema=None):
    """Mock that delegates to hass.services.async_register."""
    if hasattr(hass, "services") and hasattr(hass.services, "async_register"):
        hass.services.async_register(domain, service, func, schema=schema)


helpers_service_module.async_register_admin_service = _async_register_admin_service
sys.modules["homeassistant.helpers.service"] = helpers_service_module
helpers_module.service = helpers_service_module

# homeassistant.helpers.issue_registry stub
issue_registry_module = types.ModuleType("homeassistant.helpers.issue_registry")
issue_registry_module.IssueSeverity = types.SimpleNamespace(
    ERROR="error", WARNING="warning"
)
issue_registry_module.async_create_issue = lambda *a, **kw: None
issue_registry_module.async_delete_issue = lambda *a, **kw: None
issue_registry_module.async_get = lambda hass: types.SimpleNamespace(issues={})
sys.modules["homeassistant.helpers.issue_registry"] = issue_registry_module
helpers_module.issue_registry = issue_registry_module

# homeassistant.helpers.restore_state stub
restore_state_module = types.ModuleType("homeassistant.helpers.restore_state")
restore_state_module.RestoreEntity = _HAEntityBase
sys.modules["homeassistant.helpers.restore_state"] = restore_state_module
helpers_module.restore_state = restore_state_module

# Exceptions stub
exceptions_module = types.ModuleType("homeassistant.exceptions")
exceptions_module.ConfigEntryNotReady = type("ConfigEntryNotReady", (Exception,), {})
exceptions_module.HomeAssistantError = type("HomeAssistantError", (Exception,), {})
exceptions_module.ServiceValidationError = _ServiceValidationError
sys.modules["homeassistant.exceptions"] = exceptions_module
homeassistant.exceptions = exceptions_module

# Binary sensor stub
binary_sensor_module = types.ModuleType("homeassistant.components.binary_sensor")
binary_sensor_module.BinarySensorEntity = _BinarySensorEntity
sys.modules["homeassistant.components.binary_sensor"] = binary_sensor_module

# Sensor stub
sensor_module = types.ModuleType("homeassistant.components.sensor")
sensor_module.SensorEntity = _SensorEntity


# Define SensorStateClass as an enum-like class for proper import compatibility
class _SensorStateClass:
    MEASUREMENT = "measurement"


# Define SensorDeviceClass as an enum-like class for proper import compatibility
class _SensorDeviceClass:
    TEMPERATURE = "temperature"
    POWER = "power"
    RUNNING = "running"
    PROBLEM = "problem"
    TIMESTAMP = "timestamp"
    SPEED = "speed"
    PRESSURE = "pressure"


# Make it accessible as both module attribute and importable name
sensor_module.SensorStateClass = _SensorStateClass
sensor_module.SensorDeviceClass = _SensorDeviceClass
sys.modules["homeassistant.components.sensor"] = sensor_module

# Switch stub
switch_module = types.ModuleType("homeassistant.components.switch")
switch_module.SwitchEntity = _SwitchEntity
sys.modules["homeassistant.components.switch"] = switch_module

# Number stub
number_module = types.ModuleType("homeassistant.components.number")
number_module.NumberEntity = _NumberEntity
sys.modules["homeassistant.components.number"] = number_module

# Select stub
select_module = types.ModuleType("homeassistant.components.select")
select_module.SelectEntity = _SelectEntity
sys.modules["homeassistant.components.select"] = select_module

# Climate stub
climate_module = types.ModuleType("homeassistant.components.climate")
climate_module.ClimateEntity = _ClimateEntity
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
config_entries_module.ConfigEntryState = types.SimpleNamespace(
    LOADED="loaded",
    SETUP_ERROR="setup_error",
    NOT_LOADED="not_loaded",
)


class MockConfigFlow:
    def async_abort(self, reason=None):
        return {"reason": reason}

    def async_show_form(self, **kwargs):
        return kwargs


config_entries_module.ConfigFlow = MockConfigFlow
config_entries_module.ConfigEntry = type("ConfigEntry", (), {})
sys.modules["homeassistant.config_entries"] = config_entries_module
homeassistant.config_entries = config_entries_module

# Components diagnostics stub
diagnostics_module = types.ModuleType("homeassistant.components.diagnostics")
diagnostics_module.async_redact_data = lambda data, to_redact: {
    k: "**REDACTED**" if k in to_redact else v for k, v in data.items()
}
sys.modules["homeassistant.components.diagnostics"] = diagnostics_module

# homeassistant.util stub (needed by mapping_transform.py)
util_module = types.ModuleType("homeassistant.util")
dt_module = types.ModuleType("homeassistant.util.dt")
dt_module.now = lambda: None
util_module.dt = dt_module
sys.modules["homeassistant.util"] = util_module
sys.modules["homeassistant.util.dt"] = dt_module
homeassistant.util = util_module

# Unit of temperature stub
const_module.UnitOfTemperature = types.SimpleNamespace(CELSIUS="°C")

# Force-register all stubs
for name, module in [
    ("homeassistant.const", const_module),
    ("homeassistant.core", core_module),
    ("homeassistant.helpers", helpers_module),
    ("homeassistant.helpers.update_coordinator", update_coordinator_module),
    ("homeassistant.helpers.typing", helpers_typing_module),
    ("homeassistant.helpers.config_validation", cv_module),
    ("homeassistant.helpers.service", helpers_service_module),
    ("homeassistant.helpers.issue_registry", issue_registry_module),
    ("homeassistant.helpers.restore_state", restore_state_module),
    ("homeassistant.exceptions", exceptions_module),
    ("homeassistant.components.binary_sensor", binary_sensor_module),
    ("homeassistant.components.sensor", sensor_module),
    ("homeassistant.components.switch", switch_module),
    ("homeassistant.components.number", number_module),
    ("homeassistant.components.select", select_module),
    ("homeassistant.components.climate", climate_module),
    ("homeassistant.components.climate.const", climate_const_module),
    ("homeassistant.config_entries", config_entries_module),
    ("homeassistant.components.diagnostics", diagnostics_module),
    ("homeassistant.util", util_module),
    ("homeassistant.util.dt", dt_module),
]:
    sys.modules[name] = module
