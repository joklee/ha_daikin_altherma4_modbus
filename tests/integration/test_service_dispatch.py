"""Permanent dispatch tests for all integration services.

These tests go through ``hass.services.async_call`` (the real
Home Assistant dispatch used by automations / Developer Tools),
instead of calling the handler functions directly with
``await foo(hass, call)``.

Regression: handlers were defined as ``async def foo(hass, call)``
but ``async_register_admin_service`` expects ``Callable[[ServiceCall]]``,
so every real call failed with::

    TypeError: ... missing 1 required positional argument: 'call'
"""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.const import CONF_HOST, CONF_PORT
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.ha_daikin_altherma4_modbus.core.const import (
    CONF_UNIT_ID,
    DOMAIN,
)
from custom_components.ha_daikin_altherma4_modbus.integration import (
    services as services_module,
)
from custom_components.ha_daikin_altherma4_modbus.integration.services import (
    _SINGLE_HEATUP_TASKS,
    async_cancel_single_heatup,
    get_quiet_mode_map,
)

HOST = "192.0.2.80"


@pytest.fixture(autouse=True)
async def _cleanup_tasks():
    """Never leak background single heat-up tasks between tests."""
    yield
    for task in list(_SINGLE_HEATUP_TASKS.values()):
        task.cancel()
    if _SINGLE_HEATUP_TASKS:
        await asyncio.gather(*_SINGLE_HEATUP_TASKS.values(), return_exceptions=True)
    _SINGLE_HEATUP_TASKS.clear()


async def _setup_demo(hass):
    """Set up a demo entry (registers services via async_setup_entry)."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=f"{HOST}:502:1",
        data={CONF_HOST: HOST, CONF_PORT: 502, CONF_UNIT_ID: 1},
        options={"scan_interval": 5, "slow_scan_interval": 30, "demo_mode": True},
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id) is True
    await hass.async_block_till_done()
    return entry


def _stub_sync_io(entry):
    """Stub Modbus writes so dispatch tests stay offline."""
    manager = entry.runtime_data.manager
    manager.write_holding_register = AsyncMock(return_value=True)
    manager.write_coil_register = AsyncMock(return_value=True)
    manager.refresh_connection = AsyncMock(return_value=None)
    return manager


def _sync_cases():
    """(service, payload, assert_fn) for the 15 synchronous services."""
    quiet_mode = next(iter(get_quiet_mode_map()))
    return [
        (
            "set_operation_mode",
            {"operation_mode": "heat"},
            lambda m: m.write_holding_register.assert_called_once_with(
                "holding_3", services_module.OPERATION_MODE_MAP["heat"]
            ),
        ),
        (
            "set_dhw_state",
            {"state": True},
            lambda m: m.write_coil_register.assert_called_once(),
        ),
        (
            "set_main_zone_state",
            {"state": True},
            lambda m: m.write_coil_register.assert_called_once(),
        ),
        (
            "set_additional_zone_state",
            {"state": True},
            lambda m: m.write_coil_register.assert_called_once(),
        ),
        (
            "set_smart_grid_mode",
            {"smart_grid_mode": "recommended_on"},
            lambda m: m.write_holding_register.assert_called_once_with(
                "holding_56", services_module.get_smart_grid_mode_map()["recommended_on"]
            ),
        ),
        (
            "set_quiet_mode",
            {"quiet_mode": quiet_mode},
            lambda m: m.write_holding_register.assert_called_once_with(
                "holding_9", get_quiet_mode_map()[quiet_mode]
            ),
        ),
        (
            "set_dhw_booster_mode",
            {"booster_mode": True},
            lambda m: m.write_holding_register.assert_called_once_with("holding_13", 1),
        ),
        (
            "set_dhw_single_heatup",
            {"single_heatup": True, "setpoint": 45.0},
            lambda m: (
                m.write_holding_register.assert_any_call("holding_15", 1),
                m.write_holding_register.assert_any_call("holding_16", 4500),
            ),
        ),
        (
            "set_power_limit",
            {"power_limit": 3.5},
            lambda m: m.write_holding_register.assert_called_once_with(
                "holding_58", 3500
            ),
        ),
        (
            "set_heating_offset",
            {"offset": 2.5},
            lambda m: m.write_holding_register.assert_called_once_with("holding_54", 250),
        ),
        (
            "set_cooling_offset",
            {"offset": -1.5},
            lambda m: m.write_holding_register.assert_called_once_with(
                "holding_55", -150
            ),
        ),
        (
            "set_room_heating_setpoint",
            {"setpoint": 21.0},
            lambda m: m.write_holding_register.assert_called_once_with(
                "holding_6", 2100
            ),
        ),
        (
            "set_room_cooling_setpoint",
            {"setpoint": 25.0},
            lambda m: m.write_holding_register.assert_called_once_with(
                "holding_7", 2500
            ),
        ),
        (
            "set_additional_zone_setpoint",
            {"setpoint": 40.0},
            lambda m: m.write_holding_register.assert_called_once_with(
                "holding_63", 4000
            ),
        ),
        (
            "refresh_connection",
            {},
            lambda m: m.refresh_connection.assert_awaited_once(),
        ),
    ]


@pytest.mark.parametrize(
    "service,payload,_assert",
    _sync_cases(),
    ids=[c[0] for c in _sync_cases()],
)
async def test_dispatch_sync_services_via_hass(
    hass, enable_custom_integrations, service, payload, _assert
):
    """Every sync service must be callable via hass.services.async_call."""
    entry = await _setup_demo(hass)
    manager = _stub_sync_io(entry)

    await hass.services.async_call(
        DOMAIN,
        service,
        {"config_entry_id": entry.entry_id, **payload},
        blocking=True,
    )
    await hass.async_block_till_done()

    _assert(manager)


async def test_dispatch_start_dhw_single_heatup_via_hass(
    hass, enable_custom_integrations
):
    """start_dhw_single_heatup via dispatch: writes setpoint+request, tracks task."""
    entry = await _setup_demo(hass)
    manager = _stub_sync_io(entry)
    writer = SimpleNamespace(write_holding_register=AsyncMock(return_value=True))
    entry.runtime_data.coordinator.data_manager = writer
    manager.get_all_data = MagicMock(return_value={"input_43": {"value": 30.0}})

    await hass.services.async_call(
        DOMAIN,
        "start_dhw_single_heatup",
        {"config_entry_id": entry.entry_id, "target_temperature": 55},
        blocking=True,
    )

    writer.write_holding_register.assert_any_call("holding_16", 5500)
    writer.write_holding_register.assert_any_call("holding_15", 1)
    assert entry.entry_id in _SINGLE_HEATUP_TASKS
    assert not _SINGLE_HEATUP_TASKS[entry.entry_id].done()
    await async_cancel_single_heatup(entry.entry_id)
