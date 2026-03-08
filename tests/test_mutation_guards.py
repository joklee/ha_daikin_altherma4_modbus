import asyncio
import importlib
import sys
import types
from datetime import datetime
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
    monkeypatch.setitem(sys.modules, package_name, package_module)
    return package_name


def _load_mapping_transform_module(monkeypatch, now_values):
    package_name = _install_fake_package(monkeypatch)
    const_name = f"{package_name}.const"
    module_name = f"{package_name}.mapping_transform"

    _reset_modules(const_name, module_name)

    const_module = types.ModuleType(const_name)
    const_module.CALCULATED_SENSORS = [
        {
            "register_name": "last_compressor_run",
            "trigger_register_name": "discrete_11",
            "type": "last_triggered",
            "device_class": "timestamp",
            "name": "Last Compressor Run",
            "unit": None,
            "entity_category": None,
            "translation_key": "last_compressor_run",
        }
    ]
    monkeypatch.setitem(sys.modules, const_name, const_module)

    dt_module = types.ModuleType("homeassistant.util.dt")
    iterator = iter(now_values)
    dt_module.now = lambda: next(iterator)
    util_module = types.ModuleType("homeassistant.util")
    util_module.dt = dt_module
    monkeypatch.setitem(sys.modules, "homeassistant.util", util_module)
    monkeypatch.setitem(sys.modules, "homeassistant.util.dt", dt_module)

    return importlib.import_module(module_name)


def _load_coordinator_manager_module(monkeypatch):
    package_name = _install_fake_package(monkeypatch)
    module_name = f"{package_name}.coordinator_manager"
    const_name = f"{package_name}.const"
    coordinator_name = f"{package_name}.coordinator"

    _reset_modules(module_name, const_name, coordinator_name)

    const_module = types.ModuleType(const_name)
    const_module.DOMAIN = "ha_daikin_altherma4_modbus"
    monkeypatch.setitem(sys.modules, const_name, const_module)

    core_module = types.ModuleType("homeassistant.core")
    core_module.HomeAssistant = object
    core_module.Event = object
    monkeypatch.setitem(sys.modules, "homeassistant.core", core_module)

    update_coordinator_module = types.ModuleType(
        "homeassistant.helpers.update_coordinator"
    )

    class FakeDataUpdateCoordinator:
        def __init__(self, hass, logger, name, update_interval):
            self.hass = hass
            self.data = {}

        def async_set_updated_data(self, data):
            self.data = data

    update_coordinator_module.DataUpdateCoordinator = FakeDataUpdateCoordinator
    monkeypatch.setitem(
        sys.modules,
        "homeassistant.helpers.update_coordinator",
        update_coordinator_module,
    )

    coordinator_module = types.ModuleType(coordinator_name)
    coordinator_module.DaikinAlthermaNormalCoordinator = object
    coordinator_module.DaikinAlthermaSlowCoordinator = object
    monkeypatch.setitem(sys.modules, coordinator_name, coordinator_module)

    return importlib.import_module(module_name)


def test_last_triggered_only_updates_on_rising_edge(monkeypatch):
    t1 = datetime(2026, 3, 8, 10, 0, 0)
    t2 = datetime(2026, 3, 8, 11, 0, 0)
    mapping_module = _load_mapping_transform_module(monkeypatch, [t1, t2])
    transform = mapping_module.ModbusMappingTransform()

    transform.previous_data = {"discrete_11": {"value": 0}}
    first_data = {"discrete_11": {"value": 1}}
    transform.update_last_triggered(first_data)
    assert first_data["last_compressor_run"]["value"] == t1

    # Guard against mutation where 1->1 would incorrectly retrigger.
    transform.previous_data = {"discrete_11": {"value": 1}}
    second_data = {"discrete_11": {"value": 1}}
    transform.update_last_triggered(second_data)
    assert second_data["last_compressor_run"]["value"] == t1


@pytest.mark.asyncio
async def test_unified_write_event_schedules_and_runs_refresh(monkeypatch):
    module = _load_coordinator_manager_module(monkeypatch)

    normal = SimpleNamespace(
        async_request_refresh=AsyncMock(),
        async_add_listener=lambda _cb: (lambda: None),
    )
    slow = SimpleNamespace(
        async_request_refresh=AsyncMock(side_effect=RuntimeError("boom")),
        async_add_listener=lambda _cb: (lambda: None),
    )
    manager = SimpleNamespace(get_all_data=lambda: {})
    hass = SimpleNamespace(
        bus=SimpleNamespace(async_listen=lambda *_args: (lambda: None))
    )

    unified = module.UnifiedCoordinator(hass, manager, normal, slow)

    created_tasks = []
    real_create_task = asyncio.create_task

    def _capture_task(coro):
        task = real_create_task(coro)
        created_tasks.append(task)
        return task

    monkeypatch.setattr(module.asyncio, "create_task", _capture_task)

    unified._handle_write_event(SimpleNamespace(data={"register_name": "holding_1"}))
    assert len(created_tasks) == 1

    await created_tasks[0]
    normal.async_request_refresh.assert_awaited_once()
    slow.async_request_refresh.assert_awaited_once()
