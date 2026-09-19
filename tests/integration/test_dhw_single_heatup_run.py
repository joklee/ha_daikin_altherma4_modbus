"""Tests for the start_dhw_single_heatup background service (issue #21).

The service writes setpoint + start request, returns immediately, and a
background task watches the DHW temperature until target, timeout or
cancel - then stops the request and fires an event. All tests stay
offline via demo entries and stubbed writers.
"""

import asyncio
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
import voluptuous as vol
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.service import ServiceCall, ServiceValidationError
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
    EVENT_DHW_SINGLE_HEATUP_FINISHED,
    SERVICE_START_DHW_SINGLE_HEATUP_SCHEMA,
    async_cancel_single_heatup,
    async_start_dhw_single_heatup,
)

HOST = "192.0.2.80"
ENTRY_ID_ATTRS = {"config_entry_id": "test_entry"}


@pytest.fixture(autouse=True)
async def _cleanup_tasks(hass):
    """Never leak background tasks between tests."""
    yield
    for task in list(_SINGLE_HEATUP_TASKS.values()):
        task.cancel()
    if _SINGLE_HEATUP_TASKS:
        await asyncio.gather(*_SINGLE_HEATUP_TASKS.values(), return_exceptions=True)
    _SINGLE_HEATUP_TASKS.clear()


async def _setup_demo(hass):
    """Set up a demo entry and return it with stubbed writer/temps."""
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


def _stub_io(entry, temp):
    """Replace writer + temperature source with controllable fakes."""
    writer = SimpleNamespace(write_holding_register=AsyncMock(return_value=True))
    entry.runtime_data.coordinator.data_manager = writer
    manager = entry.runtime_data.manager
    manager.get_all_data = MagicMock(return_value={"input_43": {"value": temp}})
    return writer, manager


def _call(entry_id, **data):
    return ServiceCall(
        hass=None,
        domain=DOMAIN,
        service="start_dhw_single_heatup",
        data={"config_entry_id": entry_id, **data},
    )


def test_schema_accepts_valid_input():
    """A full valid payload passes validation."""
    validated = SERVICE_START_DHW_SINGLE_HEATUP_SCHEMA(
        {
            "config_entry_id": "abc",
            "target_temperature": 48,
            "timeout": timedelta(minutes=30),
            "hysteresis": 0.5,
        }
    )
    assert validated["target_temperature"] == 48.0
    assert validated["timeout"] == timedelta(minutes=30)


def test_schema_rejects_invalid_input():
    """Missing/out-of-range values raise vol.Invalid."""
    base = {"config_entry_id": "abc", "target_temperature": 48.0}
    with pytest.raises(vol.Invalid):
        SERVICE_START_DHW_SINGLE_HEATUP_SCHEMA(
            {"config_entry_id": "abc", "timeout": timedelta(minutes=30)}
        )
    with pytest.raises(vol.Invalid):
        SERVICE_START_DHW_SINGLE_HEATUP_SCHEMA({**base, "target_temperature": 20.0})
    with pytest.raises(vol.Invalid):
        SERVICE_START_DHW_SINGLE_HEATUP_SCHEMA(
            {**base, "timeout": timedelta(seconds=10)}
        )
    with pytest.raises(vol.Invalid):
        SERVICE_START_DHW_SINGLE_HEATUP_SCHEMA({**base, "timeout": timedelta(hours=7)})
    with pytest.raises(vol.Invalid):
        SERVICE_START_DHW_SINGLE_HEATUP_SCHEMA({**base, "hysteresis": 9.0})


async def test_start_writes_setpoint_and_request(hass, enable_custom_integrations):
    """Start writes holding_16 + holding_15 and tracks the task."""
    entry = await _setup_demo(hass)
    writer, _ = _stub_io(entry, temp=30.0)

    await async_start_dhw_single_heatup(
        hass, _call(entry.entry_id, target_temperature=48.0)
    )

    writer.write_holding_register.assert_any_call("holding_16", 4800)
    writer.write_holding_register.assert_any_call("holding_15", 1)
    assert entry.entry_id in _SINGLE_HEATUP_TASKS
    assert not _SINGLE_HEATUP_TASKS[entry.entry_id].done()


async def test_second_start_while_running_rejected(hass, enable_custom_integrations):
    """A second run for the same entry raises ServiceValidationError."""
    entry = await _setup_demo(hass)
    _stub_io(entry, temp=30.0)

    await async_start_dhw_single_heatup(
        hass, _call(entry.entry_id, target_temperature=48.0)
    )
    with pytest.raises(ServiceValidationError):
        await async_start_dhw_single_heatup(
            hass, _call(entry.entry_id, target_temperature=50.0)
        )


async def test_start_write_failure_raises_without_task(
    hass, enable_custom_integrations
):
    """A dead transport surfaces HomeAssistantError and starts nothing."""
    entry = await _setup_demo(hass)
    writer, _ = _stub_io(entry, temp=30.0)
    writer.write_holding_register = AsyncMock(side_effect=OSError("dead gateway"))
    entry.runtime_data.coordinator.data_manager = writer

    with pytest.raises(HomeAssistantError):
        await async_start_dhw_single_heatup(
            hass, _call(entry.entry_id, target_temperature=48.0)
        )
    assert entry.entry_id not in _SINGLE_HEATUP_TASKS


async def test_run_reaches_target(hass, enable_custom_integrations):
    """Target reached: stop written, event fired, task popped."""
    entry = await _setup_demo(hass)
    writer, _ = _stub_io(entry, temp=47.8)
    events = []
    hass.bus.async_listen(EVENT_DHW_SINGLE_HEATUP_FINISHED, events.append)

    await async_start_dhw_single_heatup(
        hass, _call(entry.entry_id, target_temperature=48.0, hysteresis=0.5)
    )
    # An eager task may already have finalized before registration.
    task = _SINGLE_HEATUP_TASKS.get(entry.entry_id)
    if task is not None:
        await asyncio.wait_for(task, timeout=10)
    await hass.async_block_till_done()

    writer.write_holding_register.assert_any_call("holding_15", 0)
    assert entry.entry_id not in _SINGLE_HEATUP_TASKS
    assert len(events) == 1
    assert events[0].data["outcome"] == "reached"
    assert events[0].data["target_temperature"] == 48.0
    assert events[0].data["current_temperature"] == pytest.approx(47.8)


async def test_run_timeout(hass, enable_custom_integrations, monkeypatch):
    """Timeout: stop written, timeout outcome, task popped."""
    monkeypatch.setattr(services_module, "_DHW_RUN_STATUS_POLL_INTERVAL", 0.05)
    entry = await _setup_demo(hass)
    writer, _ = _stub_io(entry, temp=30.0)
    events = []
    hass.bus.async_listen(EVENT_DHW_SINGLE_HEATUP_FINISHED, events.append)

    await async_start_dhw_single_heatup(
        hass,
        _call(entry.entry_id, target_temperature=48.0, timeout=timedelta(seconds=1)),
    )
    task = _SINGLE_HEATUP_TASKS.get(entry.entry_id)
    if task is not None:
        await asyncio.wait_for(task, timeout=10)
    await hass.async_block_till_done()

    writer.write_holding_register.assert_any_call("holding_15", 0)
    assert entry.entry_id not in _SINGLE_HEATUP_TASKS
    assert len(events) == 1
    assert events[0].data["outcome"] == "timeout"


async def test_cancel_stops_run(hass, enable_custom_integrations, monkeypatch):
    """Explicit cancel ends the run with a cancelled outcome."""
    monkeypatch.setattr(services_module, "_DHW_RUN_STATUS_POLL_INTERVAL", 30.0)
    entry = await _setup_demo(hass)
    writer, _ = _stub_io(entry, temp=30.0)
    events = []
    hass.bus.async_listen(EVENT_DHW_SINGLE_HEATUP_FINISHED, events.append)

    await async_start_dhw_single_heatup(
        hass,
        _call(entry.entry_id, target_temperature=48.0, timeout=timedelta(hours=2)),
    )
    assert entry.entry_id in _SINGLE_HEATUP_TASKS

    await async_cancel_single_heatup(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.entry_id not in _SINGLE_HEATUP_TASKS
    writer.write_holding_register.assert_any_call("holding_15", 0)
    assert len(events) == 1
    assert events[0].data["outcome"] == "cancelled"


async def test_unload_cancels_running_heatup(hass, enable_custom_integrations):
    """Unload tears down a running heat-up (no writes after teardown)."""
    entry = await _setup_demo(hass)
    _stub_io(entry, temp=30.0)

    await async_start_dhw_single_heatup(
        hass,
        _call(entry.entry_id, target_temperature=48.0, timeout=timedelta(hours=2)),
    )
    assert entry.entry_id in _SINGLE_HEATUP_TASKS

    assert await hass.config_entries.async_unload(entry.entry_id) is True
    await hass.async_block_till_done()

    assert entry.entry_id not in _SINGLE_HEATUP_TASKS


async def test_run_without_temperature_reading_waits_for_timeout(
    hass, enable_custom_integrations, monkeypatch
):
    """Unknown temperature never counts as reached."""
    monkeypatch.setattr(services_module, "_DHW_RUN_STATUS_POLL_INTERVAL", 0.05)
    entry = await _setup_demo(hass)
    writer, manager = _stub_io(entry, temp=None)
    manager.get_all_data = MagicMock(return_value={})
    events = []
    hass.bus.async_listen(EVENT_DHW_SINGLE_HEATUP_FINISHED, events.append)

    await async_start_dhw_single_heatup(
        hass,
        _call(entry.entry_id, target_temperature=48.0, timeout=timedelta(seconds=1)),
    )
    task = _SINGLE_HEATUP_TASKS.get(entry.entry_id)
    if task is not None:
        await asyncio.wait_for(task, timeout=10)
    await hass.async_block_till_done()

    assert events[0].data["outcome"] == "timeout"
    assert events[0].data["current_temperature"] is None
    writer.write_holding_register.assert_any_call("holding_15", 0)
