import importlib
import sys
import types
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest


def _reset_modules(*names: str) -> None:
    for name in names:
        sys.modules.pop(name, None)


def _install_fake_package(monkeypatch) -> str:
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


def _install_common_homeassistant_stubs(monkeypatch) -> None:
    homeassistant = types.ModuleType("homeassistant")
    monkeypatch.setitem(sys.modules, "homeassistant", homeassistant)

    const_module = types.ModuleType("homeassistant.const")
    const_module.CONF_HOST = "host"
    const_module.CONF_PORT = "port"
    const_module.EntityCategory = SimpleNamespace(DIAGNOSTIC="diagnostic")
    monkeypatch.setitem(sys.modules, "homeassistant.const", const_module)

    core_module = types.ModuleType("homeassistant.core")
    core_module.HomeAssistant = object
    core_module.Event = object
    monkeypatch.setitem(sys.modules, "homeassistant.core", core_module)

    helpers_module = types.ModuleType("homeassistant.helpers")
    monkeypatch.setitem(sys.modules, "homeassistant.helpers", helpers_module)

    update_coordinator_module = types.ModuleType(
        "homeassistant.helpers.update_coordinator"
    )

    class FakeDataUpdateCoordinator:
        def __init__(self, hass, logger, name, update_interval):
            self.hass = hass
            self.data = {}

        async def async_config_entry_first_refresh(self):
            return None

        async def async_request_refresh(self):
            return None

        def async_add_listener(self, callback):
            return lambda: None

        def async_set_updated_data(self, data):
            self.data = data

    class FakeCoordinatorEntity:
        def __init__(self, coordinator):
            self.coordinator = coordinator

    update_coordinator_module.DataUpdateCoordinator = FakeDataUpdateCoordinator
    update_coordinator_module.CoordinatorEntity = FakeCoordinatorEntity
    update_coordinator_module.UpdateFailed = Exception
    monkeypatch.setitem(
        sys.modules,
        "homeassistant.helpers.update_coordinator",
        update_coordinator_module,
    )

    components_module = types.ModuleType("homeassistant.components")
    monkeypatch.setitem(sys.modules, "homeassistant.components", components_module)

    sensor_component_module = types.ModuleType("homeassistant.components.sensor")
    sensor_component_module.SensorEntity = object
    monkeypatch.setitem(
        sys.modules, "homeassistant.components.sensor", sensor_component_module
    )


def _load_config_flow_module(monkeypatch):
    _install_common_homeassistant_stubs(monkeypatch)
    package_name = _install_fake_package(monkeypatch)

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

    const_module_name = f"{package_name}.const"
    const_module = types.ModuleType(const_module_name)
    const_module.DOMAIN = "ha_daikin_altherma4_modbus"
    const_module.SLOW_SCAN_INTERVAL = 600
    monkeypatch.setitem(sys.modules, const_module_name, const_module)

    module_name = f"{package_name}.config_flow"
    _reset_modules(module_name)
    return importlib.import_module(module_name)


def _load_integration_module(monkeypatch):
    package_name = "custom_components.ha_daikin_altherma4_modbus"
    const_name = f"{package_name}.const"
    coordinator_manager_name = f"{package_name}.coordinator_manager"
    modbus_client_name = f"{package_name}.modbus_client"

    _reset_modules(
        package_name, const_name, coordinator_manager_name, modbus_client_name
    )

    const_module = types.ModuleType(const_name)
    const_module.DOMAIN = "ha_daikin_altherma4_modbus"
    const_module.SLOW_SCAN_INTERVAL = 600
    const_module.NORMAL_SCAN_INTERVAL = 10
    monkeypatch.setitem(sys.modules, const_name, const_module)

    coordinator_manager_module = types.ModuleType(coordinator_manager_name)

    class FakeCoordinator:
        def __init__(self):
            self.async_config_entry_first_refresh = AsyncMock()
            self.data = {}

    class FakeCoordinatorManager:
        last_instance = None

        def __init__(self, hass, host, port, normal_interval, slow_interval, demo_mode):
            self.normal = FakeCoordinator()
            self.slow = FakeCoordinator()
            self.host = host
            self.port = port
            FakeCoordinatorManager.last_instance = self

        async def async_setup(self):
            await self.normal.async_config_entry_first_refresh()
            await self.slow.async_config_entry_first_refresh()

        def get_coordinator(self, coordinator_type):
            return self.normal if coordinator_type == "normal" else self.slow

        async def async_shutdown(self, disconnect_clients=True):
            return None

        def get_all_data(self):
            return {}

    class FakeUnifiedCoordinator:
        def __init__(self, hass, manager, normal_coordinator, slow_coordinator):
            self.data = {}
            self.async_setup = AsyncMock()

        async def async_shutdown(self):
            return None

    coordinator_manager_module.CoordinatorManager = FakeCoordinatorManager
    coordinator_manager_module.UnifiedCoordinator = FakeUnifiedCoordinator
    monkeypatch.setitem(
        sys.modules, coordinator_manager_name, coordinator_manager_module
    )

    modbus_client_module = types.ModuleType(modbus_client_name)

    class FakeRealModbusTcpClient:
        async_close_cached_client = AsyncMock()

    modbus_client_module.RealModbusTcpClient = FakeRealModbusTcpClient
    monkeypatch.setitem(sys.modules, modbus_client_name, modbus_client_module)

    return importlib.import_module(package_name), FakeCoordinatorManager


def _load_sensor_module(monkeypatch):
    _install_common_homeassistant_stubs(monkeypatch)
    package_name = _install_fake_package(monkeypatch)

    const_module_name = f"{package_name}.const"
    sensor_module_name = f"{package_name}.sensor"
    _reset_modules(const_module_name, sensor_module_name)

    const_module = types.ModuleType(const_module_name)
    const_module.DOMAIN = "ha_daikin_altherma4_modbus"
    const_module.INPUT_DEVICE_INFO = {}
    const_module.CALCULATED_DEVICE_INFO = {}
    const_module.INPUT_REGISTERS = []
    const_module.CALCULATED_SENSORS = []
    monkeypatch.setitem(sys.modules, const_module_name, const_module)

    return importlib.import_module(sensor_module_name)


@pytest.mark.asyncio
async def test_config_flow_user_step_separates_data_and_options(monkeypatch):
    config_flow = _load_config_flow_module(monkeypatch)
    flow = config_flow.ConfigFlow()

    result = await flow.async_step_user(
        {
            "host": "192.168.1.20",
            "port": 1502,
            "scan_interval": 15,
            "slow_scan_interval": 900,
            "electric_power_sensor": " sensor.grid_power ",
            "demo_mode": True,
        }
    )

    assert result["type"] == "create_entry"
    assert result["data"] == {"host": "192.168.1.20", "port": 1502}
    assert result["options"] == {
        "scan_interval": 15,
        "slow_scan_interval": 900,
        "electric_power_sensor": "sensor.grid_power",
        "demo_mode": True,
    }


@pytest.mark.asyncio
async def test_options_flow_updates_only_options(monkeypatch):
    config_flow = _load_config_flow_module(monkeypatch)
    entry = SimpleNamespace(
        data={"host": "192.168.1.10", "port": 502},
        options={"scan_interval": 10, "slow_scan_interval": 600, "demo_mode": False},
    )
    flow = config_flow.OptionsFlow(entry)

    result = await flow.async_step_init(
        {
            "scan_interval": 20,
            "slow_scan_interval": 1200,
            "electric_power_sensor": "sensor.new_power",
            "demo_mode": True,
        }
    )

    assert result["type"] == "create_entry"
    assert "host" not in result["data"]
    assert "port" not in result["data"]
    assert result["data"] == {
        "scan_interval": 20,
        "slow_scan_interval": 1200,
        "electric_power_sensor": "sensor.new_power",
        "demo_mode": True,
    }
    assert entry.data == {"host": "192.168.1.10", "port": 502}


@pytest.mark.asyncio
async def test_setup_entry_runs_single_initial_refresh_per_coordinator(monkeypatch):
    integration, manager_cls = _load_integration_module(monkeypatch)

    hass = SimpleNamespace(
        data={},
        config_entries=SimpleNamespace(
            async_forward_entry_setups=AsyncMock(return_value=True)
        ),
    )
    entry = SimpleNamespace(
        entry_id="entry-id",
        data={"host": "192.168.1.10", "port": 502},
        options={"scan_interval": 10, "slow_scan_interval": 600, "demo_mode": False},
    )

    setup_ok = await integration.async_setup_entry(hass, entry)

    assert setup_ok is True
    manager = manager_cls.last_instance
    assert manager is not None
    assert manager.normal.async_config_entry_first_refresh.await_count == 1
    assert manager.slow.async_config_entry_first_refresh.await_count == 1


def test_external_electric_power_sensor_uses_options_and_fallback(monkeypatch):
    sensor_module = _load_sensor_module(monkeypatch)

    states = {
        "sensor.external_power": SimpleNamespace(state="123.4"),
    }
    hass = SimpleNamespace(
        states=SimpleNamespace(get=lambda entity_id: states.get(entity_id))
    )
    coordinator = SimpleNamespace(hass=hass)

    sensor = sensor_module.ExternalElectricPowerSensor(
        coordinator=coordinator,
        entry=SimpleNamespace(
            data={}, options={"electric_power_sensor": "sensor.external_power"}
        ),
        unique_id="test",
        unit="W",
        device_class="power",
    )
    assert sensor.available is True
    assert sensor.native_value == 123.4

    legacy_sensor = sensor_module.ExternalElectricPowerSensor(
        coordinator=coordinator,
        entry=SimpleNamespace(
            data={"electric_power_sensor": "sensor.external_power"},
            options={},
        ),
        unique_id="test_legacy",
        unit="W",
        device_class="power",
    )
    assert legacy_sensor.available is True
    assert legacy_sensor.native_value == 123.4

    unavailable_sensor = sensor_module.ExternalElectricPowerSensor(
        coordinator=coordinator,
        entry=SimpleNamespace(data={}, options={}),
        unique_id="test_unavailable",
        unit="W",
        device_class="power",
    )
    assert unavailable_sensor.available is False
    assert unavailable_sensor.native_value is None
