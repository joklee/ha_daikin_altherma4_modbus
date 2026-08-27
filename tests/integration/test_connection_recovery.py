"""Connection-recovery integration test.

Exercises the real production data path for the normal coordinator::

    controllable fake client (I/O boundary)
        ↓
    ModbusDataManager / RegisterRepository
        ↓
    DaikinAlthermaNormalCoordinator
        ↓
    DaikinInputSensor

The test drives the coordinator through

    connected → timeout → (un)available → reconnect → connected

and asserts the *observable* behaviour of the production code. It does **not**
mock the coordinator, the data manager or the entity.
"""

from types import SimpleNamespace

import pytest

from custom_components.ha_daikin_altherma4_modbus.core.const import DOMAIN
from custom_components.ha_daikin_altherma4_modbus.core.exceptions import (
    ModbusReadException,
    ModbusTimeoutException,
)
from custom_components.ha_daikin_altherma4_modbus.core.register_constants import (
    INPUT_DEVICE_INFO,
)
from custom_components.ha_daikin_altherma4_modbus.core.register_types import TEMP16
from custom_components.ha_daikin_altherma4_modbus.entities.sensor import (
    DaikinInputSensor,
)
from custom_components.ha_daikin_altherma4_modbus.integration.coordinator import (
    DaikinAlthermaNormalCoordinator,
)
from tests.fakes.modbus import FakeModbusResponse

# input_40 is "Leaving water temperature PHE" (TEMP16, scaling 0.01).
TEMP16_RAW = 2150  # 21.50 °C
TEMP16_EXPECTED = 21.5


class _RecoverableClient:
    """Fake Modbus client that can be switched between success and failure.

    Uses the same FakeModbusResponse used by the rest of the test suite for
    valid responses, and raises a production Modbus I/O exception (from
    ``core.exceptions``) while ``fail`` is set, simulating a timeout at the
    transport boundary. It is intentionally a small, local fake: the only thing
    this test does not drive is FAILURE toggling, which the shared
    ``FakeModbusClient`` does not expose.
    """

    def __init__(self, failure_cls):
        self.fail = False
        self.connected = True
        self._failure_cls = failure_cls

    async def connect(self):
        self.connected = True

    async def disconnect(self):
        self.connected = False

    async def read_input_registers(self, address, count):
        if self.fail:
            raise self._failure_cls("simulated input register timeout")
        # Register array as 1-based; index 40 carries the TEMP16 raw value.
        regs = [32767] * 88
        regs[40] = TEMP16_RAW
        return FakeModbusResponse(regs, address, count)

    async def read_holding_registers(self, address, count):
        return FakeModbusResponse([32767] * 88, address, count)

    async def read_discrete_inputs(self, address, count):
        bits = [False] * 27
        bits[1] = True
        return FakeModbusResponse(bits, address, count, is_bits=True)

    async def read_coils(self, address, count):
        return FakeModbusResponse([False] * 4, address, count, is_bits=True)


def _make_coordinator(fail_cls):
    """Build a real DaikinAlthermaNormalCoordinator with a faked I/O boundary."""
    hass = SimpleNamespace(
        config_entries=SimpleNamespace(async_entries=lambda domain: [])
    )
    coordinator = DaikinAlthermaNormalCoordinator(
        hass, "192.0.2.1", 502, scan_interval=10, demo_mode=False
    )
    client = _RecoverableClient(fail_cls)
    coordinator.data_manager.client = client
    coordinator.last_update_success = None
    return coordinator, client


def _make_sensor(coordinator):
    """Bind a real DaikinInputSensor to the coordinator and entry."""
    entry = SimpleNamespace(
        entry_id="test", data={"host": "192.0.2.1", "port": 502}, options={}
    )
    return DaikinInputSensor(
        coordinator=coordinator,
        entry=entry,
        address=40,
        unit="°C",
        data_type=TEMP16,
        count=1,
        enum_map=None,
        register_name="input_40",
        device_class="temperature",
        unique_id=f"{DOMAIN}_input_40",
        translation_key="input_40",
        device_info=INPUT_DEVICE_INFO,
    )


async def _refresh(coordinator):
    """Test-harness refresh mirroring the real DataUpdateCoordinator lifecycle.

    The ``homeassistant`` stub in this project does not implement
    ``last_update_success`` or ``async_config_entry_first_refresh``; this small
    wrapper reproduces exactly the semantics the real DUC applies, so the test
    can observe the availability the integration relies on.
    """
    try:
        data = await coordinator._async_update_data()
    except Exception:  # UpdateFailed is ``Exception`` in the stub.
        coordinator.last_update_success = False
        raise
    else:
        coordinator.last_update_success = True
        return data


@pytest.mark.parametrize(
    "fail_cls",
    [
        ModbusTimeoutException,
        ModbusReadException,
    ],
)
async def test_connection_recovery_cycle(fail_cls):
    """A communication failure at the transport can be recovered from.

    Phase 1 - connected
    Phase 2 - timeout
    Phase 3 - (error / unavailable)
    Phase 4 - reconnect
    Phase 5 - available

    NOTE on the failure phase: the production RegisterRepository swallows
    ``ModbusReadException``/``ModbusTimeoutException`` during input-register
    reads and returns an *empty* block list instead of propagating. As a
    result ``coordinator.last_update_success`` stays ``True`` and the
    coordinator itself does not raise ``UpdateFailed``. The *entity* still
    becomes unavailable only because ``input_40`` is absent from the
    (now empty) coordinator data. This test documents that real behaviour
    instead of artificially forcing ``last_update_success=False``.

    Only the input-register read is failed on purpose. Failing the
    discrete-input read instead would trigger ``_retry_read_discrete_inputs``,
    which in real mode calls ``reconnect_with_new_client()`` and creates a
    real ``RealModbusTcpClient`` (a real network attempt). Keeping discrete
    reads healthy keeps this test deterministic and offline while still
    exercising the genuine input-register failure path.
    """
    # Phase 1 - connected
    coordinator, client = _make_coordinator(fail_cls)
    sensor = _make_sensor(coordinator)

    await _refresh(coordinator)
    assert coordinator.last_update_success is True
    assert coordinator.data.get("input_40") is not None
    assert sensor.available is True
    assert sensor.native_value == pytest.approx(TEMP16_EXPECTED)

    # Phase 2 - simulate timeout at the transport boundary
    client.fail = True

    # The failure is swallowed by the repository: no UpdateFailed is raised
    # and the coordinator reports a successful (if empty) update.
    await _refresh(coordinator)
    assert "input_40" not in coordinator.data

    # Phase 3 - visible (entity-level) unavailability.
    assert sensor.available is False
    assert sensor.native_value is None

    # Phase 4 - reconnect: the transport is healthy again.
    client.fail = False
    await _refresh(coordinator)

    # Phase 5 - recovered.
    assert coordinator.last_update_success is True
    assert coordinator.data.get("input_40") is not None
    assert sensor.available is True
    assert sensor.native_value == pytest.approx(TEMP16_EXPECTED)
