"""Tests for diagnostics.py."""
from types import SimpleNamespace

import pytest

from custom_components.ha_daikin_altherma4_modbus.diagnostics import (
    async_get_config_entry_diagnostics,
)


def _make_entry(host="192.168.1.100"):
    entry = SimpleNamespace(
        data={"host": host, "port": 502},
        options={"demo_mode": False},
    )
    coord = SimpleNamespace(
        data={"test": {"value": 1, "input_type": "input"}},
        last_update_success=True,
        update_interval=SimpleNamespace(total_seconds=lambda: 10),
    )
    manager = SimpleNamespace(
        host=host, port=502, demo_mode=False, coordinators={"normal": coord},
    )
    entry.runtime_data = SimpleNamespace(manager=manager)
    return entry


@pytest.mark.asyncio
async def test_diagnostics_redacts_host():
    """Test diagnostics redacts host information."""
    result = await async_get_config_entry_diagnostics(SimpleNamespace(), _make_entry())
    assert result["connection"]["host"] == "**REDACTED**"


@pytest.mark.asyncio
async def test_diagnostics_has_expected_structure():
    """Test diagnostics result has expected keys."""
    result = await async_get_config_entry_diagnostics(SimpleNamespace(), _make_entry())
    assert "config_entry_data" in result
    assert "config_entry_options" in result
    assert "connection" in result
    assert "coordinator_statuses" in result
    assert "coordinator_data" in result


@pytest.mark.asyncio
async def test_diagnostics_coordinator_status():
    """Test coordinator status info."""
    result = await async_get_config_entry_diagnostics(SimpleNamespace(), _make_entry())
    status = result["coordinator_statuses"]["normal"]
    assert status["last_update_success"] is True
    assert status["data_points"] == 1
    assert status["update_interval"] == 10


@pytest.mark.asyncio
async def test_diagnostics_empty_coordinator_data():
    """Test diagnostics with empty coordinator data."""
    entry = SimpleNamespace(data={}, options={})
    coord = SimpleNamespace(
        data={}, last_update_success=True, update_interval=None,
    )
    manager = SimpleNamespace(
        host="localhost", port=502, demo_mode=False,
        coordinators={"slow": coord},
    )
    entry.runtime_data = SimpleNamespace(manager=manager)

    result = await async_get_config_entry_diagnostics(SimpleNamespace(), entry)
    assert result["coordinator_statuses"]["slow"]["data_points"] == 0
    assert result["coordinator_statuses"]["slow"]["update_interval"] is None


@pytest.mark.asyncio
async def test_diagnostics_coordinator_data_serialization():
    """Test coordinator data serialization."""
    entry = SimpleNamespace(data={}, options={})
    coord = SimpleNamespace(
        data={"key1": {"nested": "value"}, "key2": 42},
        last_update_success=True,
        update_interval=SimpleNamespace(total_seconds=lambda: 30),
    )
    manager = SimpleNamespace(
        host="localhost", port=502, demo_mode=True,
        coordinators={"main": coord},
    )
    entry.runtime_data = SimpleNamespace(manager=manager)

    result = await async_get_config_entry_diagnostics(SimpleNamespace(), entry)
    data = result["coordinator_data"]["main"]
    assert data["key1"]["nested"] == "value"
    assert data["key2"]["value"] == 42