"""Unit tests for ModbusDataManager orchestration (no HA instance needed).

The manager is a thin facade over session/repository/mapping: the session
and repository are stubbed at the I/O boundary while the real mapping
transform runs, so fetch paths are exercised end to end without hardware.
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from custom_components.ha_daikin_altherma4_modbus.core.data_manager import (
    ModbusDataManager,
)
from custom_components.ha_daikin_altherma4_modbus.modbus.transport_session import (
    ModbusTransportSession,
)

_MISSING = object()


def _manager(*, client=_MISSING):
    if client is _MISSING:
        client = object()
    manager = ModbusDataManager("192.168.1.100", 502)
    manager._session = SimpleNamespace(ensure_connection=AsyncMock(), client=client)
    return manager


def _repository(**overrides):
    defaults = {
        "read_input_blocks": AsyncMock(return_value=[([0] * 67, 21, 87, 21)]),
        "read_discrete_inputs": AsyncMock(return_value=[False] * 26),
        "read_coils": AsyncMock(return_value=[False] * 3),
        "read_holding_blocks": AsyncMock(return_value=[([0] * 80, 1, 80, 1)]),
        "write_holding_register": AsyncMock(return_value=True),
        "write_coil_register": AsyncMock(return_value=True),
        "read_raw_snapshot": AsyncMock(return_value=({"input": {}}, {})),
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


async def test_fetch_coils_data():
    manager = _manager()
    manager._repository = _repository()
    data = await manager.fetch_coils_data()
    assert isinstance(data, dict)
    manager._repository.read_coils.assert_awaited_once()


async def test_fetch_holding_registers_data():
    manager = _manager()
    manager._repository = _repository()
    data = await manager.fetch_holding_registers_data()
    assert isinstance(data, dict)
    manager._repository.read_holding_blocks.assert_awaited_once()


async def test_refresh_paths():
    manager = _manager()
    manager._repository = _repository()
    assert isinstance(await manager.refresh_holding_registers(), dict)
    assert isinstance(await manager.refresh_coils(), dict)
    assert isinstance(await manager.refresh_all_data(), dict)
    assert isinstance(await manager.fetch_all_data(), dict)


async def test_fetch_without_client_returns_empty():
    """No client: every fetch warns and returns an empty dict."""
    manager = _manager(client=None)
    manager._repository = _repository()
    assert await manager.fetch_input_registers_data() == {}
    assert await manager.fetch_discrete_inputs_data() == {}
    assert await manager.fetch_coils_data() == {}
    assert await manager.fetch_holding_registers_data() == {}
    assert await manager.refresh_holding_registers() == {}
    assert await manager.refresh_coils() == {}
    assert await manager.refresh_all_data() == {}
    assert await manager.fetch_all_data() == {}


async def test_none_results_are_skipped():
    """None bit-reads produce empty data without failing."""
    manager = _manager()
    manager._repository = _repository(
        read_discrete_inputs=AsyncMock(return_value=None),
        read_coils=AsyncMock(return_value=None),
    )
    assert await manager.fetch_discrete_inputs_data() == {}
    assert await manager.fetch_coils_data() == {}


async def test_writes_update_coordinator_data():
    manager = _manager()
    manager._repository = _repository()
    manager.coordinator = SimpleNamespace(
        data={"holding_3": {"value": 0}},
        async_set_updated_data=AsyncMock(),
    )
    assert await manager.write_holding_register("holding_3", 1) is True
    assert manager.coordinator.data["holding_3"]["value"] == 1
    assert await manager.write_coil_register("coil_1", True) is True


async def test_writes_without_result_skip_coordinator_update():
    manager = _manager()
    manager._repository = _repository(
        write_holding_register=AsyncMock(return_value=None),
        write_coil_register=AsyncMock(return_value=None),
    )
    manager.coordinator = SimpleNamespace(data={}, async_set_updated_data=AsyncMock())
    assert await manager.write_holding_register("holding_3", 1) is None
    assert await manager.write_coil_register("coil_1", True) is None
    manager.coordinator.async_set_updated_data.assert_not_called()


async def test_coordinator_notify_failure_is_swallowed():
    """A failing async_set_updated_data only warns."""

    async def raising_notify(_data):
        raise RuntimeError("listener boom")

    manager = _manager()
    manager._repository = _repository()
    manager.coordinator = SimpleNamespace(
        data={"holding_3": {"value": 0}},
        async_set_updated_data=raising_notify,
    )
    assert await manager.write_holding_register("holding_3", 1) is True


async def test_refresh_connection_success_and_failure():
    manager = _manager()
    manager._session.reconnect_with_new_client = AsyncMock()
    await manager.refresh_connection()
    manager._session.reconnect_with_new_client.assert_awaited_once()

    manager._session.reconnect_with_new_client = AsyncMock(
        side_effect=OSError("link down")
    )
    with pytest.raises(OSError):
        await manager.refresh_connection()


async def test_read_raw_snapshot_delegates():
    manager = _manager()
    manager._repository = _repository()
    snapshot = await manager.read_raw_snapshot()
    assert snapshot == ({"input": {}}, {})
    manager._repository.read_raw_snapshot.assert_awaited_once()


def test_client_property_and_error_shim():
    manager = _manager()
    sentinel = object()
    manager.client = sentinel
    assert manager.client is sentinel
    assert ModbusDataManager._is_modbus_error([1, 2, 3]) is False
    assert ModbusTransportSession.is_modbus_error([1, 2, 3]) is False


def test_update_last_triggered_delegates():
    manager = _manager()
    manager._update_last_triggered({"input_40": {"value": 2150}})
