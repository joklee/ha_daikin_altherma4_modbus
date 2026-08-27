"""Tests for mapping_transform.py."""

from types import SimpleNamespace

import pytest

from custom_components.ha_daikin_altherma4_modbus.core.mapping_transform import (
    ModbusMappingTransform,
)
from custom_components.ha_daikin_altherma4_modbus.core.register_types import (
    INT16,
)


def _make_register_item(
    address, register_name, enum_map=None, data_type=INT16, input_type="input"
):
    item = SimpleNamespace(
        address=address,
        register_name=register_name,
        enum_map=enum_map,
        data_type=data_type,
        input_type=input_type,
    )
    return item


def _make_processed_item(
    raw_value, register_name, input_type="input", address=1, item=None
):
    from custom_components.ha_daikin_altherma4_modbus.core.data_types import (
        ProcessedRegisterItem,
    )

    return ProcessedRegisterItem(
        raw_value=raw_value,
        input_type=input_type,
        address=address,
        description=f"Test {address}",
        item=item or _make_register_item(address, register_name),
    )


def test_process_register_block_basic():
    """Test process_register_block builds data dict."""
    transform = ModbusMappingTransform()
    register_data = SimpleNamespace(registers=[0, 2500, 0])
    register_list = [
        _make_register_item(1, "input_1"),
    ]
    result = transform.process_register_block(
        register_data, register_list, 0, 10, 0, "input", "Input Register"
    )
    assert "input_1" in result
    assert result["input_1"].raw_value == 2500


def test_process_register_block_index_error():
    """Test process_register_block raises on IndexError."""
    transform = ModbusMappingTransform()
    register_data = SimpleNamespace(registers=[0])
    register_list = [
        _make_register_item(5, "input_5"),
    ]
    with pytest.raises(IndexError):
        transform.process_register_block(
            register_data, register_list, 0, 10, 0, "input", "Input Register"
        )


def test_apply_register_processing_scaled():
    """Test apply_register_processing scales signed values."""
    transform = ModbusMappingTransform()
    item = _make_register_item(1, "input_1", data_type=INT16)
    processed = _make_processed_item(2500, "input_1", item=item)
    previous = {}
    result = transform.apply_register_processing("input_1", processed, previous)
    # INT16 has scaling=1, so value stays 2500
    assert result.value == 2500


def test_apply_register_processing_special_value():
    """Test apply_register_processing handles special values."""
    transform = ModbusMappingTransform()
    item = _make_register_item(1, "input_1", data_type=INT16)
    processed = _make_processed_item(32767, "input_1", item=item)
    previous = {}
    result = transform.apply_register_processing("input_1", processed, previous)
    assert result.value == 32767


def test_process_input_register_block_skips_unsupported():
    """Test process_input_register_block skips 32767."""
    transform = ModbusMappingTransform()
    # Need enough registers for addresses 1 and 2 (indices 1 and 2)
    register_data = SimpleNamespace(registers=[0, 0, 32767])
    register_list = [
        _make_register_item(1, "input_1"),
        _make_register_item(2, "input_2"),
    ]
    result = transform.process_input_register_block(
        register_data, register_list, 0, 10, 0
    )
    assert "input_1" in result
    assert "input_2" not in result


def test_process_holding_register_block():
    """Test process_holding_register_block processes all registers."""
    transform = ModbusMappingTransform()
    register_data = SimpleNamespace(registers=[0, 1, 2])
    register_list = [
        _make_register_item(1, "holding_1"),
        _make_register_item(2, "holding_2"),
    ]
    result = transform.process_holding_register_block(
        register_data, register_list, 0, 10, 0
    )
    assert "holding_1" in result
    assert "holding_2" in result


def test_process_bit_sensors():
    """Test process_bit_sensors processes bit results."""
    transform = ModbusMappingTransform()
    result = SimpleNamespace(bits=[False, True, False])
    sensor_list = [_make_register_item(1, "bit_1")]
    data = transform.process_bit_sensors(result, sensor_list, "discrete")
    # bit at index 1 is True, so value should be 1
    assert data["bit_1"].value == 1


def test_process_bit_sensors_out_of_range():
    """Test process_bit_sensors handles out-of-range address."""
    transform = ModbusMappingTransform()
    result = SimpleNamespace(bits=[False])
    sensor_list = [_make_register_item(5, "bit_5")]
    data = transform.process_bit_sensors(result, sensor_list, "discrete")
    assert "bit_5" not in data


def test_update_last_triggered(monkeypatch):
    """Test update_last_triggered updates timestamps on 0->1 transition.

    NOTE: other tests in this and the ``unit`` package manipulate
    ``sys.modules`` (and even re-create the ``mapping_transform`` module under
    the same import name), which can leave a *different* module object than the
    one that actually defined :class:`ModbusMappingTransform`. Patching the
    module-global ``CALCULATED_SENSORS`` via ``monkeypatch.setitem`` on the
    method's own ``__globals__`` (and stubbing ``homeassistant.util`` via
    ``monkeypatch.setitem`` too) makes this test immune to that and guarantees
    teardown even when an assertion fails.
    """
    import sys
    from datetime import datetime, timezone
    from types import ModuleType

    from custom_components.ha_daikin_altherma4_modbus.core.register_types import (
        CalculatedRegister,
    )

    # Patch CALCULATED_SENSORS on the exact globals dict the method reads, so
    # duplicate/parallel module instances cannot break the lookup.
    method_globals = ModbusMappingTransform.update_last_triggered.__globals__
    calc_item = CalculatedRegister(
        name="Last Compressor",
        address=0,
        input_type="calculated",
        register_name="last_compressor",
        data_type=INT16,
        trigger_register_name="input_31",
    )
    monkeypatch.setitem(method_globals, "CALCULATED_SENSORS", [calc_item])

    # Provide a deterministic homeassistant.util.dt.now() -> fixed_time.
    fixed_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    util_mod = ModuleType("homeassistant.util")
    dt_mod = ModuleType("homeassistant.util.dt")
    dt_mod.now = lambda: fixed_time
    util_mod.dt = dt_mod
    monkeypatch.setitem(sys.modules, "homeassistant.util", util_mod)
    monkeypatch.setitem(sys.modules, "homeassistant.util.dt", dt_mod)

    transform = ModbusMappingTransform()
    transform.last_triggered = {}

    # First call: compressor goes from off to on
    data = {
        "input_31": {"value": 1},
    }
    transform.update_last_triggered(data)
    assert "last_compressor" in transform.last_triggered
    assert transform.last_triggered["last_compressor"] == fixed_time

    # Second call: compressor stays on, timestamp should not change
    old_ts = transform.last_triggered["last_compressor"]
    transform.update_last_triggered(data)
    assert transform.last_triggered["last_compressor"] == old_ts
