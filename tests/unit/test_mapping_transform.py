"""Tests for ModbusMappingTransform register processing.

Covers:
* signed/unsigned register conversion
* register block processing (input/holding)
* bit sensor processing
* last-triggered timestamp tracking
"""

import importlib
import importlib.util
import os
import sys
import types
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from custom_components.ha_daikin_altherma4_modbus.core.mapping_transform import (
    ModbusMappingTransform,
)
from custom_components.ha_daikin_altherma4_modbus.core.register_types import (
    INT16,
)


def _ensure_homeassistant_stubs() -> None:
    """Ensure homeassistant stubs are available.

    The stubs are installed by ``tests/fixtures/homeassistant.py`` at session
    start; this fallback only guards against running a single test outside the
    pytest session.
    """
    if "homeassistant" not in sys.modules:
        from tests.fixtures.homeassistant import install_homeassistant_stubs

        install_homeassistant_stubs()


_ensure_homeassistant_stubs()


def _load_mapping_module(monkeypatch):
    """Load mapping_transform module with mocked dependencies."""
    package_name = "custom_components.ha_daikin_altherma4_modbus"

    def mock_to_signed_16bit(value):
        """Convert unsigned 16-bit to signed."""
        if value >= 32768:
            return value - 65536
        return value

    # Return a simple dict that can be subscripted
    class MockPayload(dict):
        pass

    def mock_update_value_if_changed(
        unique_id, raw_value, previous_data, register_type="register", **kwargs
    ):
        return MockPayload({"value": raw_value, "register_name": unique_id})

    # Create common module mock
    common_name = f"{package_name}.common"
    common_module = types.ModuleType(common_name)
    common_module.__path__ = []  # Mark as a package
    common_module.to_signed_16bit = mock_to_signed_16bit
    common_module.get_register_value = lambda data: (
        int(data) if data is not None else 0,
    )
    common_module.get_register_scale = lambda data: (0.01,)
    common_module.update_value_if_changed = mock_update_value_if_changed
    common_module.is_unavailable_value = lambda v: (v in (32765, 32766, 32767),)
    common_module.is_problematic_value = lambda v: (v == 32765,)

    common_module.to_signed_16bit = mock_to_signed_16bit
    common_module.get_register_value = lambda data: (
        data.get("value") if isinstance(data, dict) else None
    )
    common_module.get_register_scale = lambda data: (
        data.get("scale") if isinstance(data, dict) else None
    )

    common_module.update_value_if_changed = mock_update_value_if_changed
    common_module.is_unavailable_value = lambda v: (
        v in {32765, 32766, 32767} or v is None
    )

    # Also need to set in sys.modules before importing mapping_transform
    monkeypatch.setitem(sys.modules, common_name, common_module)
    monkeypatch.setitem(sys.modules, common_name, common_module)

    # Mock common.helpers to avoid import issues
    helpers_name = f"{common_name}.helpers"
    helpers_module = types.ModuleType(helpers_name)
    helpers_module.to_signed_16bit = mock_to_signed_16bit
    helpers_module.get_register_value = common_module.get_register_value
    helpers_module.get_register_scale = common_module.get_register_scale
    helpers_module.update_value_if_changed = common_module.update_value_if_changed
    helpers_module.is_unavailable_value = common_module.is_unavailable_value
    helpers_module.BaseEntityMixin = object
    monkeypatch.setitem(sys.modules, helpers_name, helpers_module)
    monkeypatch.setitem(sys.modules, helpers_name, helpers_module)

    # Create core module mock
    core_name = f"{package_name}.core"
    core_module = types.ModuleType(core_name)
    core_module.__path__ = []  # Mark as a package

    # Create and set up submodules
    mapping_transform_module = types.ModuleType(f"{core_name}.mapping_transform")
    core_module.mapping_transform = mapping_transform_module
    monkeypatch.setitem(
        sys.modules, f"{core_name}.mapping_transform", mapping_transform_module
    )

    monkeypatch.setitem(sys.modules, core_name, core_module)
    monkeypatch.setitem(sys.modules, core_name, core_module)

    # Create const module mock with SPECIAL_REGISTER_VALUES
    const_name = f"{core_name}.const"
    const_module = types.ModuleType(const_name)
    const_module.SPECIAL_REGISTER_NOT_SUPPORTED = 32767
    const_module.SPECIAL_REGISTER_NOT_AVAILABLE = 32766
    const_module.SPECIAL_REGISTER_WAITING = 32765
    const_module.SPECIAL_REGISTER_VALUES = frozenset({32765, 32766, 32767})
    monkeypatch.setitem(sys.modules, const_name, const_module)
    monkeypatch.setitem(sys.modules, const_name, const_module)

    # Mock data_manager
    data_manager_name = f"{core_name}.data_manager"
    data_manager_module = types.ModuleType(data_manager_name)
    monkeypatch.setitem(sys.modules, data_manager_name, data_manager_module)
    monkeypatch.setitem(sys.modules, data_manager_name, data_manager_module)

    # Mock data_types
    data_types_name = f"{core_name}.data_types"
    data_types_module = types.ModuleType(data_types_name)
    monkeypatch.setitem(sys.modules, data_types_name, data_types_module)
    monkeypatch.setitem(sys.modules, data_types_name, data_types_module)

    # Mock register_constants
    register_constants_name = f"{core_name}.register_constants"
    register_constants_module = types.ModuleType(register_constants_name)
    register_constants_module.CALCULATED_SENSORS = {}
    monkeypatch.setitem(sys.modules, register_constants_name, register_constants_module)
    monkeypatch.setitem(sys.modules, register_constants_name, register_constants_module)

    # Mock register_types
    register_types_name = f"{core_name}.register_types"
    register_types_module = types.ModuleType(register_types_name)
    register_types_module.RegisterDefinition = object
    monkeypatch.setitem(sys.modules, register_types_name, register_types_module)
    monkeypatch.setitem(sys.modules, register_types_name, register_types_module)

    # Load the real data_types module from filesystem
    data_types_path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "..",
        "custom_components",
        "ha_daikin_altherma4_modbus",
        "core",
        "data_types.py",
    )

    data_types_spec = importlib.util.spec_from_file_location(
        f"{core_name}.data_types", data_types_path
    )
    data_types_module = importlib.util.module_from_spec(data_types_spec)
    monkeypatch.setitem(sys.modules, f"{core_name}.data_types", data_types_module)
    data_types_spec.loader.exec_module(data_types_module)

    # Remove mapping_transform from cache if already loaded
    mod_to_remove = f"{core_name}.mapping_transform"
    if mod_to_remove in sys.modules:
        del sys.modules[mod_to_remove]

    # Load the real module from filesystem
    module_path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "..",
        "custom_components",
        "ha_daikin_altherma4_modbus",
        "core",
        "mapping_transform.py",
    )

    # Load the module from the filesystem
    spec = importlib.util.spec_from_file_location(
        f"{core_name}.mapping_transform", module_path
    )
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, f"{core_name}.mapping_transform", module)
    spec.loader.exec_module(module)

    return module


class TestSignedConversion:
    """Tests for signed register conversion in mapping_transform."""

    def setup_method(self):
        """Ensure stubs are available before each test."""
        _ensure_homeassistant_stubs()

    def test_apply_register_processing_signed_conversion(self, monkeypatch):
        """Test that signed registers are converted from unsigned to signed."""
        mapping_module = _load_mapping_module(monkeypatch)

        # Create mock data_type with signed=True
        mock_data_type = SimpleNamespace(
            name="Int16", signed=True, bits=16, scaling=1, range=(-32768, 32767)
        )

        # Create processed_item with unsigned value (65534 = -2 in signed)
        processed_item = SimpleNamespace(
            raw_value=65534,  # -2 in signed 16-bit
            input_type="holding",
            address=55,
            description="Holding Register 55",
            item=SimpleNamespace(
                data_type=mock_data_type, address=55, register_name="holding_55"
            ),
        )

        # Create mock previous_data
        previous_data = MagicMock()
        previous_data.get = lambda k, default=None: default

        # Apply processing
        result = mapping_module.ModbusMappingTransform.apply_register_processing(
            "holding_55", processed_item, previous_data
        )

        # Verify signed conversion was applied
        assert result["value"] == -2, f"Expected -2 but got {result['value']}"

    def test_apply_register_processing_unsigned_stays_unchanged(self, monkeypatch):
        """Test that unsigned registers are not converted."""
        mapping_module = _load_mapping_module(monkeypatch)

        # Create mock data_type with signed=False
        mock_data_type = SimpleNamespace(
            name="UInt16", signed=False, bits=16, scaling=1, range=(0, 65535)
        )

        # Create processed_item with unsigned value
        processed_item = SimpleNamespace(
            raw_value=100,
            input_type="holding",
            address=10,
            description="Holding Register 10",
            item=SimpleNamespace(
                data_type=mock_data_type, address=10, register_name="holding_10"
            ),
        )

        previous_data = MagicMock()
        previous_data.get = lambda k, default=None: default

        result = mapping_module.ModbusMappingTransform.apply_register_processing(
            "holding_10", processed_item, previous_data
        )

        # Verify value stays unchanged (no signed conversion)
        assert result["value"] == 100

    def test_apply_register_processing_signed_with_scaling(self, monkeypatch):
        """Test that signed conversion happens before scaling."""
        mapping_module = _load_mapping_module(monkeypatch)

        # Create mock data_type with signed=True and scaling=0.01
        mock_data_type = SimpleNamespace(
            name="Temp16", signed=True, bits=16, scaling=0.01, range=(-327.68, 327.67)
        )

        # 65534 = -2 in signed, then -2 * 0.01 = -0.02
        processed_item = SimpleNamespace(
            raw_value=65534,
            input_type="input",
            address=40,
            description="Input Register 40",
            item=SimpleNamespace(
                data_type=mock_data_type, address=40, register_name="input_40"
            ),
        )

        previous_data = MagicMock()
        previous_data.get = lambda k, default=None: default

        result = mapping_module.ModbusMappingTransform.apply_register_processing(
            "input_40", processed_item, previous_data
        )

        # Verify: signed conversion first (-2), then scaling (-2 * 0.01 = -0.02)
        assert result["value"] == -0.02, f"Expected -0.02 but got {result['value']}"


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
    """Test process_holding_register_block builds data dict."""
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
