"""Config flow tests for ha_daikin_altherma4_modbus integration."""

import importlib
import sys
import types
from pathlib import Path
from types import SimpleNamespace

import pytest


def _reset_modules(*names: str) -> None:
    """Reset modules for clean testing."""
    for name in names:
        sys.modules.pop(name, None)


def _install_fake_package(monkeypatch) -> str:
    """Install fake package for testing."""
    package_name = "custom_components.ha_daikin_altherma4_modbus"
    package_path = (
        Path(__file__).resolve().parents[1]
        / "custom_components"
        / "ha_daikin_altherma4_modbus"
    )
    package_module = types.ModuleType(package_name)
    package_module.__path__ = [str(package_path)]
    package_module.NORMAL_SCAN_INTERVAL = 10
    monkeypatch.setitem(sys.modules, package_name, package_module)
    return package_name


def _install_common_homeassistant_stubs(monkeypatch):
    """Install common Home Assistant stubs."""
    # Mock homeassistant base module
    homeassistant = types.ModuleType("homeassistant")
    monkeypatch.setitem(sys.modules, "homeassistant", homeassistant)

    # Mock homeassistant.config_entries
    config_entries_module = types.ModuleType("homeassistant.config_entries")
    config_entries_module.CONN_CLASS_LOCAL_POLL = "local_poll"

    class FakeConfigFlow:
        def __init_subclass__(cls, **kwargs):
            return super().__init_subclass__()

        def async_create_entry(self, title, data, options=None):
            return {
                "type": "create_entry",
                "title": title,
                "data": data,
                "options": options,
            }

        def async_show_form(self, **kwargs):
            return {"type": "form", **kwargs}

    class FakeOptionsFlow:
        def __init__(self, config_entry):
            self._config_entry = config_entry
            self.hass = SimpleNamespace(config_entries=SimpleNamespace())

        def async_create_entry(self, title, data):
            return {"type": "create_entry", "title": title, "data": data}

        def async_show_form(self, **kwargs):
            return {"type": "form", **kwargs}

    config_entries_module.ConfigFlow = FakeConfigFlow
    config_entries_module.OptionsFlow = FakeOptionsFlow
    monkeypatch.setitem(
        sys.modules, "homeassistant.config_entries", config_entries_module
    )

    # Mock homeassistant.const
    const_module = types.ModuleType("homeassistant.const")
    const_module.CONF_HOST = "host"
    const_module.CONF_PORT = "port"
    monkeypatch.setitem(sys.modules, "homeassistant.const", const_module)

    # Mock voluptuous
    voluptuous_module = types.ModuleType("voluptuous")

    def _identity(value, default=None):
        return value

    class FakeSchema:
        def __init__(self, schema):
            self.schema = schema

        def __call__(self, value):
            return value

    voluptuous_module.Required = _identity
    voluptuous_module.Optional = _identity
    voluptuous_module.Schema = FakeSchema
    monkeypatch.setitem(sys.modules, "voluptuous", voluptuous_module)


def _load_config_flow_module(monkeypatch):
    """Load config flow module with mocked dependencies."""
    _install_common_homeassistant_stubs(monkeypatch)
    package_name = _install_fake_package(monkeypatch)

    # Mock const module
    const_name = f"{package_name}.const"
    const_module = types.ModuleType(const_name)
    const_module.DOMAIN = "ha_daikin_altherma4_modbus"
    const_module.SLOW_SCAN_INTERVAL = 600
    monkeypatch.setitem(sys.modules, const_name, const_module)

    # Mock init module with NORMAL_SCAN_INTERVAL
    init_name = f"{package_name}"
    init_module = types.ModuleType(init_name)
    init_module.NORMAL_SCAN_INTERVAL = 10
    monkeypatch.setitem(sys.modules, init_name, init_module)

    # Mock config entry utils
    config_entry_utils_name = f"{package_name}.config_entry_utils"
    config_entry_utils_module = types.ModuleType(config_entry_utils_name)

    def entry_value(entry, key, default=None):
        return entry.options.get(key, default)

    config_entry_utils_module.entry_value = entry_value
    monkeypatch.setitem(sys.modules, config_entry_utils_name, config_entry_utils_module)

    # Create the actual config_flow module by loading the real file
    config_flow_path = (
        Path(__file__).resolve().parents[1]
        / "custom_components"
        / "ha_daikin_altherma4_modbus"
        / "config_flow.py"
    )

    # Read the file content and modify imports
    with open(config_flow_path, "r") as f:
        content = f.read()

    # Replace relative imports with absolute imports
    content = content.replace(
        "from . import NORMAL_SCAN_INTERVAL",
        f"from {package_name} import NORMAL_SCAN_INTERVAL",
    )
    content = content.replace(
        "from .config_entry_utils import entry_value",
        f"from {config_entry_utils_name} import entry_value",
    )
    content = content.replace(
        "from .const import DOMAIN, SLOW_SCAN_INTERVAL",
        f"from {const_name} import DOMAIN, SLOW_SCAN_INTERVAL",
    )

    # Create a temporary file with modified content
    import tempfile

    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as tmp_file:
        tmp_file.write(content)
        tmp_file_path = tmp_file.name

    try:
        # Load the modified config_flow module
        spec = importlib.util.spec_from_file_location("config_flow", tmp_file_path)
        config_flow_module = importlib.util.module_from_spec(spec)

        # Install it in sys.modules before loading
        module_name = f"{package_name}.config_flow"
        sys.modules[module_name] = config_flow_module

        # Load the module
        spec.loader.exec_module(config_flow_module)

        return config_flow_module
    finally:
        # Clean up temporary file
        import os

        os.unlink(tmp_file_path)


@pytest.mark.asyncio
async def test_config_flow_success(monkeypatch):
    """Test successful config flow execution."""
    config_flow_module = _load_config_flow_module(monkeypatch)
    flow = config_flow_module.ConfigFlow()

    result = await flow.async_step_user(
        {
            "host": "192.168.1.100",
            "port": 502,
            "scan_interval": 15,
            "slow_scan_interval": 300,
            "electric_power_sensor": "sensor.power",
            "demo_mode": True,
        }
    )

    assert result["type"] == "create_entry"
    assert result["title"] == "Daikin Altherma 4 (192.168.1.100)"
    assert result["data"] == {"host": "192.168.1.100", "port": 502}
    assert result["options"] == {
        "scan_interval": 15,
        "slow_scan_interval": 300,
        "electric_power_sensor": "sensor.power",
        "demo_mode": True,
    }


@pytest.mark.asyncio
async def test_config_flow_invalid_host(monkeypatch):
    """Test config flow with invalid host."""
    config_flow_module = _load_config_flow_module(monkeypatch)
    flow = config_flow_module.ConfigFlow()

    result = await flow.async_step_user(
        {
            "host": "invalid host with spaces",
            "port": 502,
            "scan_interval": 15,
            "slow_scan_interval": 300,
            "demo_mode": False,
        }
    )

    assert result["type"] == "form"
    assert "errors" in result
    assert result["errors"]["host"] == "invalid_host"


@pytest.mark.asyncio
async def test_config_flow_connection_error(monkeypatch):
    """Test config flow with connection error - simulated via invalid host."""
    config_flow_module = _load_config_flow_module(monkeypatch)
    flow = config_flow_module.ConfigFlow()

    # Since the real config_flow doesn't do connection testing,
    # we simulate a connection error by using an invalid port
    result = await flow.async_step_user(
        {
            "host": "192.168.1.100",
            "port": 70000,  # Invalid port to simulate connection issue
            "scan_interval": 15,
            "slow_scan_interval": 300,
            "demo_mode": False,
        }
    )

    assert result["type"] == "form"
    assert "errors" in result
    assert result["errors"]["port"] == "invalid_port"


@pytest.mark.asyncio
async def test_options_flow(monkeypatch):
    """Test options flow execution."""
    config_flow_module = _load_config_flow_module(monkeypatch)

    # Create a mock config entry
    config_entry = SimpleNamespace(
        entry_id="test_entry_1",
        options={
            "scan_interval": 15,
            "slow_scan_interval": 300,
            "demo_mode": False,
            "electric_power_sensor": "existing_sensor",
        },
    )

    # Create options flow instance
    options_flow = config_flow_module.OptionsFlow(config_entry)

    # Mock user input with updated values
    user_input = {
        "scan_interval": 20,
        "slow_scan_interval": 400,
        "demo_mode": True,
        "electric_power_sensor": "new_sensor",
    }

    # Execute the options step
    result = await options_flow.async_step_init(user_input)

    # Verify successful creation of entry
    assert result["type"] == "create_entry"
    assert result["title"] == ""

    # Verify the updated options
    options_data = result["data"]
    assert options_data["scan_interval"] == 20
    assert options_data["slow_scan_interval"] == 400
    assert options_data["demo_mode"] is True
    assert options_data["electric_power_sensor"] == "new_sensor"


@pytest.mark.asyncio
async def test_options_flow_validation_errors(monkeypatch):
    """Test options flow validation errors."""
    config_flow_module = _load_config_flow_module(monkeypatch)

    config_entry = SimpleNamespace(
        entry_id="test_entry_1",
        options={
            "scan_interval": 15,
            "slow_scan_interval": 300,
            "demo_mode": False,
        },
    )

    options_flow = config_flow_module.OptionsFlow(config_entry)

    # Test invalid scan_interval (<= 0)
    user_input = {
        "scan_interval": 0,
        "slow_scan_interval": 300,
        "demo_mode": False,
    }

    result = await options_flow.async_step_init(user_input)

    # Should return form with errors
    assert result["type"] == "form"
    assert "errors" in result
    assert "scan_interval" in result["errors"]
    assert result["errors"]["scan_interval"] == "invalid_scan_interval"

    # Test slow_scan_interval < scan_interval
    user_input = {
        "scan_interval": 20,
        "slow_scan_interval": 10,  # Less than scan_interval
        "demo_mode": False,
    }

    result = await options_flow.async_step_init(user_input)

    # Should return form with errors
    assert result["type"] == "form"
    assert "errors" in result
    assert "slow_scan_interval" in result["errors"]
    assert result["errors"]["slow_scan_interval"] == "slow_must_be_gte_scan"


@pytest.mark.asyncio
async def test_options_flow_show_form_with_current_values(monkeypatch):
    """Test that options flow shows form with current values."""
    config_flow_module = _load_config_flow_module(monkeypatch)

    config_entry = SimpleNamespace(
        entry_id="test_entry_1",
        options={
            "scan_interval": 25,
            "slow_scan_interval": 500,
            "demo_mode": True,
            "electric_power_sensor": "test_sensor",
        },
    )

    options_flow = config_flow_module.OptionsFlow(config_entry)

    # Call without user input to show form
    result = await options_flow.async_step_init(None)

    # Verify form is shown
    assert result["type"] == "form"
    assert result["step_id"] == "init"

    # Verify schema contains current values as defaults
    schema = result["data_schema"].schema
    assert "scan_interval" in schema
    assert "slow_scan_interval" in schema
    assert "demo_mode" in schema
    assert "electric_power_sensor" in schema
