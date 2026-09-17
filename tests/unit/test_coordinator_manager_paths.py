"""Unit tests for CoordinatorManager/UnifiedCoordinator paths (no HA needed)."""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from custom_components.ha_daikin_altherma4_modbus.integration.coordinator_manager import (
    CoordinatorManager,
    UnifiedCoordinator,
    UnifiedWriteProxy,
)


def _coordinator(
    *,
    shutdown=None,
    client=None,
    request_refresh=None,
    add_listener=None,
):
    coordinator = SimpleNamespace()
    if shutdown is not None:
        coordinator.async_shutdown = shutdown
    coordinator.data_manager = SimpleNamespace(client=client)
    coordinator.async_request_refresh = request_refresh or AsyncMock(return_value=None)
    coordinator.async_add_listener = add_listener or MagicMock(return_value=MagicMock())
    return coordinator


def _manager(normal=None, slow=None):
    manager = CoordinatorManager.__new__(CoordinatorManager)
    manager.normal_coordinator = normal or _coordinator()
    manager.slow_coordinator = slow or _coordinator()
    manager.coordinators = {
        "normal": manager.normal_coordinator,
        "slow": manager.slow_coordinator,
    }
    manager.get_all_data = MagicMock(return_value={"a": 1})
    return manager


async def test_shutdown_disconnects_connected_clients():
    client = SimpleNamespace(connected=True, disconnect=AsyncMock())
    manager = _manager(
        normal=_coordinator(shutdown=AsyncMock(), client=client),
        slow=_coordinator(client=SimpleNamespace(connected=False)),
    )
    await manager.async_shutdown(disconnect_clients=True)
    client.disconnect.assert_awaited_once()


async def test_shutdown_skips_disconnect_when_not_requested():
    client = SimpleNamespace(connected=True, disconnect=AsyncMock())
    manager = _manager(normal=_coordinator(client=client))
    await manager.async_shutdown(disconnect_clients=False)
    client.disconnect.assert_not_called()


async def test_shutdown_without_client_and_with_failing_shutdown():
    async def boom():
        raise RuntimeError("shutdown failed")

    manager = _manager(
        normal=_coordinator(shutdown=boom, client=None),
        slow=_coordinator(),
    )
    await manager.async_shutdown(disconnect_clients=True)


async def test_get_coordinator_and_delegates():
    manager = _manager()
    assert manager.get_coordinator("normal") is manager.normal_coordinator
    assert manager.get_coordinator("nope") is None
    await manager.async_request_refresh_all()
    manager.normal_coordinator.async_request_refresh.assert_awaited_once()
    manager.slow_coordinator.async_request_refresh.assert_awaited_once()


async def test_refresh_connection_success_and_failure():
    manager = _manager()
    manager.normal_coordinator.data_manager.refresh_connection = AsyncMock()
    manager.slow_coordinator.data_manager.refresh_connection = AsyncMock()
    await manager.refresh_connection()

    manager.normal_coordinator.data_manager.refresh_connection = AsyncMock(
        side_effect=OSError("down")
    )
    try:
        await manager.refresh_connection()
    except OSError:
        pass
    else:
        raise AssertionError("expected OSError")


async def test_write_proxy_fires_event_only_on_result():
    hass = SimpleNamespace(bus=SimpleNamespace(async_fire=MagicMock()))
    normal = _coordinator()
    normal.hass = hass
    slow_data_manager = SimpleNamespace(
        write_holding_register=AsyncMock(return_value=None),
        write_coil_register=AsyncMock(return_value=True),
    )
    slow = _coordinator()
    slow.data_manager = slow_data_manager
    proxy = UnifiedWriteProxy(normal, slow)

    assert await proxy.write_holding_register("holding_3", 1) is None
    hass.bus.async_fire.assert_not_called()

    slow_data_manager.write_holding_register = AsyncMock(return_value=True)
    assert await proxy.write_holding_register("holding_3", 1) is True
    hass.bus.async_fire.assert_called_once()

    assert await proxy.write_coil_register("coil_1", True) is True
    assert hass.bus.async_fire.call_count == 2


def _unified(manager=None):
    manager = manager or _manager()
    manager.async_request_refresh_all = AsyncMock()
    hass = SimpleNamespace(
        bus=SimpleNamespace(async_listen=MagicMock(return_value=MagicMock())),
        loop=None,
        async_create_task=None,
    )
    unified = UnifiedCoordinator.__new__(UnifiedCoordinator)
    # Bypass DataUpdateCoordinator.__init__ (needs a real hass instance).
    unified.manager = manager
    unified.normal_coordinator = manager.normal_coordinator
    unified.slow_coordinator = manager.slow_coordinator
    unified.data_manager = UnifiedWriteProxy(
        manager.normal_coordinator, manager.slow_coordinator
    )
    unified._unsubscribers = []
    unified._refresh_tasks = set()
    unified.hass = hass
    unified.async_set_updated_data = MagicMock()
    return unified, hass


async def test_unified_setup_and_shutdown():
    unified, _ = _unified()
    await unified.async_setup()
    assert len(unified._unsubscribers) == 3
    await unified.async_shutdown()
    assert unified._unsubscribers == []


async def test_unified_source_update_pushes_merged_data():
    unified, _ = _unified()
    unified._handle_source_coordinator_update()
    unified.async_set_updated_data.assert_called_once_with({"a": 1})


async def test_unified_write_event_schedules_refresh():
    unified, hass = _unified()

    def immediate(coro):
        return asyncio.ensure_future(coro)

    hass.async_create_task = immediate
    hass.loop = asyncio.get_running_loop()
    event = SimpleNamespace(data={"register_name": "holding_3", "value": 1})
    # call_soon_threadsafe runs on the test loop; pump until refresh happens.
    unified._handle_write_event(event)
    for _ in range(100):
        if unified.slow_coordinator.async_request_refresh.await_count >= 1:
            break
        await asyncio.sleep(0)
    assert unified.slow_coordinator.async_request_refresh.await_count >= 1
    assert unified.normal_coordinator.async_request_refresh.await_count >= 1


async def test_unified_manual_update_and_shutdown_with_tasks():
    unified, _ = _unified()
    assert await unified._async_update_data() == {"a": 1}

    async def hanging():
        await asyncio.sleep(60)

    task = asyncio.ensure_future(hanging())
    unified._refresh_tasks.add(task)
    await unified.async_shutdown()
    assert unified._refresh_tasks == set()
    assert task.cancelled() or task.done()
