"""Test mapping_transform module for signed register conversion."""

import importlib
import sys
import types
from types import SimpleNamespace
from unittest.mock import MagicMock


def _ensure_homeassistant_stubs():
    """Ensure homeassistant stubs are available."""
    modules_to_remove = [k for k in sys.modules.keys() if k.startswith("homeassistant")]
    for module in modules_to_remove:
        del sys.modules[module]

    homeassistant = types.ModuleType("homeassistant")
    homeassistant.__path__ = []
    sys.modules["homeassistant"] = homeassistant

    exceptions_module = types.ModuleType("homeassistant.exceptions")
    exceptions_module.ConfigEntryNotReady = Exception
    sys.modules["homeassistant.exceptions"] = exceptions_module

    const_module = types.ModuleType("homeassistant.const")
    const_module.EntityCategory = types.SimpleNamespace(DIAGNOSTIC="diagnostic")
    sys.modules["homeassistant.const"] = const_module

    core_module = types.ModuleType("homeassistant.core")
    core_module.Event = object
    core_module.HomeAssistant = object
    sys.modules["homeassistant.core"] = core_module

    helpers_module = types.ModuleType("homeassistant.helpers")
    helpers_module.__path__ = []
    sys.modules["homeassistant.helpers"] = helpers_module

    helpers_typing_module = types.ModuleType("homeassistant.helpers.typing")
    helpers_typing_module.ConfigType = dict
    sys.modules["homeassistant.helpers.typing"] = helpers_typing_module

    update_coordinator_module = types.ModuleType(
        "homeassistant.helpers.update_coordinator"
    )
    update_coordinator_module.DataUpdateCoordinator = object
    update_coordinator_module.CoordinatorEntity = object
    update_coordinator_module.UpdateFailed = Exception
    sys.modules["homeassistant.helpers.update_coordinator"] = update_coordinator_module


_ensure_homeassistant_stubs()


def _load_mapping_module(monkeypatch):
    """Load mapping_transform module with mocked dependencies."""
    package_name = "custom_components.ha_daikin_altherma4_modbus"

    # Create common module mock
    common_name = f"{package_name}.common"
    common_module = types.ModuleType(common_name)

    def mock_to_signed_16bit(value):
        """Convert unsigned 16-bit to signed."""
        if value >= 32768:
            return value - 65536
        return value

    common_module.to_signed_16bit = mock_to_signed_16bit
    common_module.get_register_value = lambda data: (
        data.get("value") if isinstance(data, dict) else None
    )
    common_module.get_register_scale = lambda data: (
        data.get("scale") if isinstance(data, dict) else None
    )

    # Return a simple dict that can be subscripted
    class MockPayload(dict):
        pass

    def mock_update_value_if_changed(
        unique_id, raw_value, previous_data, register_type="register", **kwargs
    ):
        return MockPayload({"value": raw_value, "register_name": unique_id})

    common_module.update_value_if_changed = mock_update_value_if_changed
    common_module.is_unavailable_value = lambda v: (
        v in {32765, 32766, 32767} or v is None
    )

    # Also need to set in sys.modules before importing mapping_transform
    sys.modules[common_name] = common_module
    monkeypatch.setitem(sys.modules, common_name, common_module)

    # Create const module mock with SPECIAL_REGISTER_VALUES
    const_name = f"{package_name}.const"
    const_module = types.ModuleType(const_name)
    const_module.SPECIAL_REGISTER_NOT_SUPPORTED = 32767
    const_module.SPECIAL_REGISTER_NOT_AVAILABLE = 32766
    const_module.SPECIAL_REGISTER_WAITING = 32765
    const_module.SPECIAL_REGISTER_VALUES = frozenset({32765, 32766, 32767})
    sys.modules[const_name] = const_module
    monkeypatch.setitem(sys.modules, const_name, const_module)

    # Remove mapping_transform from cache if already loaded
    mod_to_remove = f"{package_name}.mapping_transform"
    if mod_to_remove in sys.modules:
        del sys.modules[mod_to_remove]

    # Also remove common to force reload
    if common_name in sys.modules:
        del sys.modules[common_name]
    sys.modules[common_name] = common_module

    # Load the module
    module_name = f"{package_name}.mapping_transform"
    return importlib.import_module(module_name)


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
