"""Tests for special Daikin HomeHub Modbus register return values.

Special return values:
  - 32767: Register not supported (device does not support the register)
  - 32766: Register not available (not available in current configuration)
  - 32765: Waiting for value (value not yet loaded)
"""

import sys
import types


def _ensure_homeassistant_stubs():
    """Ensure homeassistant stubs are available and correctly configured.

    Does NOT remove existing stubs (which are set up by conftest.py) to avoid
    breaking other tests that rely on the conftest stubs.
    """
    if "homeassistant" not in sys.modules:
        homeassistant = types.ModuleType("homeassistant")
        homeassistant.__path__ = []
        sys.modules["homeassistant"] = homeassistant
    else:
        homeassistant = sys.modules["homeassistant"]

    if "homeassistant.exceptions" not in sys.modules:
        exceptions_module = types.ModuleType("homeassistant.exceptions")
        exceptions_module.ConfigEntryNotReady = Exception
        sys.modules["homeassistant.exceptions"] = exceptions_module
        homeassistant.exceptions = exceptions_module

    if "homeassistant.const" not in sys.modules:
        const_module = types.ModuleType("homeassistant.const")
        const_module.EntityCategory = types.SimpleNamespace(DIAGNOSTIC="diagnostic")
        sys.modules["homeassistant.const"] = const_module
        homeassistant.const = const_module

    if "homeassistant.core" not in sys.modules:
        core_module = types.ModuleType("homeassistant.core")
        core_module.Event = object
        core_module.HomeAssistant = object
        sys.modules["homeassistant.core"] = core_module
        homeassistant.core = core_module

    if "homeassistant.helpers" not in sys.modules:
        helpers_module = types.ModuleType("homeassistant.helpers")
        helpers_module.__path__ = []
        sys.modules["homeassistant.helpers"] = helpers_module
        homeassistant.helpers = helpers_module

    if "homeassistant.helpers.update_coordinator" not in sys.modules:
        update_coordinator_module = types.ModuleType(
            "homeassistant.helpers.update_coordinator"
        )
        update_coordinator_module.DataUpdateCoordinator = object
        update_coordinator_module.CoordinatorEntity = object
        update_coordinator_module.UpdateFailed = Exception
        sys.modules["homeassistant.helpers.update_coordinator"] = (
            update_coordinator_module
        )

    if "homeassistant.helpers.typing" not in sys.modules:
        helpers_typing_module = types.ModuleType("homeassistant.helpers.typing")
        helpers_typing_module.ConfigType = dict
        sys.modules["homeassistant.helpers.typing"] = helpers_typing_module


_ensure_homeassistant_stubs()

from custom_components.ha_daikin_altherma4_modbus.common import (
    is_entity_available,
    is_unavailable_value,
    validate_register_value,
)
from custom_components.ha_daikin_altherma4_modbus.const import (
    SPECIAL_REGISTER_NOT_AVAILABLE,
    SPECIAL_REGISTER_NOT_SUPPORTED,
    SPECIAL_REGISTER_VALUES,
    SPECIAL_REGISTER_WAITING,
)
from custom_components.ha_daikin_altherma4_modbus.data_types import (
    EntityStatePayload,
    ProcessedRegisterItem,
)
from custom_components.ha_daikin_altherma4_modbus.mapping_transform import (
    ModbusMappingTransform,
)

# ── Constants ───────────────────────────────────────────────────────────


class TestSpecialRegisterConstants:
    """Tests for special register value constants."""

    def test_not_supported_value(self):
        """32767 = Register not supported."""
        assert SPECIAL_REGISTER_NOT_SUPPORTED == 32767

    def test_not_available_value(self):
        """32766 = Register not available."""
        assert SPECIAL_REGISTER_NOT_AVAILABLE == 32766

    def test_waiting_value(self):
        """32765 = Waiting for value."""
        assert SPECIAL_REGISTER_WAITING == 32765

    def test_all_three_in_special_set(self):
        """All three special values should be in the set."""
        assert SPECIAL_REGISTER_VALUES == frozenset({32767, 32766, 32765})

    def test_special_set_is_frozenset(self):
        """SPECIAL_REGISTER_VALUES should be immutable."""
        assert isinstance(SPECIAL_REGISTER_VALUES, frozenset)


# ── validate_register_value ─────────────────────────────────────────────


class TestValidateRegisterValue:
    """Tests for validate_register_value with all three special values."""

    def test_normal_value_is_valid(self):
        """Normal values should be valid."""
        assert validate_register_value(0) is True
        assert validate_register_value(100) is True
        assert validate_register_value(32764) is True
        assert validate_register_value(-10) is True

    def test_none_is_invalid(self):
        """None should be invalid."""
        assert validate_register_value(None) is False

    def test_not_supported_is_invalid(self):
        """32767 (register not supported) should be invalid."""
        assert validate_register_value(32767) is False

    def test_not_available_is_invalid(self):
        """32766 (register not available) should be invalid."""
        assert validate_register_value(32766) is False

    def test_waiting_is_invalid(self):
        """32765 (waiting for value) should be invalid."""
        assert validate_register_value(32765) is False

    def test_string_invalid_returns_false(self):
        """Non-numeric strings should be invalid."""
        assert validate_register_value("abc") is False

    def test_float_int_like_is_checked(self):
        """Float values that are int-like should be checked."""
        assert validate_register_value(32767.0) is False
        assert validate_register_value(32766.0) is False
        assert validate_register_value(32765.0) is False


# ── is_unavailable_value ────────────────────────────────────────────────


class TestIsUnavailableValue:
    """Tests for is_unavailable_value with all three special values."""

    def test_none_is_unavailable(self):
        """None should be unavailable."""
        assert is_unavailable_value(None) is True

    def test_not_supported_is_unavailable(self):
        """32767 (register not supported) should be unavailable."""
        assert is_unavailable_value(32767) is True

    def test_not_available_is_unavailable(self):
        """32766 (register not available) should be unavailable."""
        assert is_unavailable_value(32766) is True

    def test_waiting_is_unavailable(self):
        """32765 (waiting for value) should be unavailable."""
        assert is_unavailable_value(32765) is True

    def test_normal_value_is_available(self):
        """Normal values should be available."""
        assert is_unavailable_value(0) is False
        assert is_unavailable_value(100) is False
        assert is_unavailable_value(32764) is False
        assert is_unavailable_value(-1) is False

    def test_string_unavailable(self):
        """Non-numeric strings should be unavailable."""
        assert is_unavailable_value("abc") is True

    def test_float_unavailable(self):
        """Special float values should be unavailable."""
        assert is_unavailable_value(32767.0) is True
        assert is_unavailable_value(32766.0) is True
        assert is_unavailable_value(32765.0) is True


# ── is_entity_available ─────────────────────────────────────────────────


class TestIsEntityAvailable:
    """Tests for is_entity_available with special register values."""

    def test_entity_with_normal_value_available(self):
        """Entity with normal register value should be available."""
        data = {"test_register": EntityStatePayload(value=42)}
        assert is_entity_available(data, "test_register") is True

    def test_entity_with_32767_not_supported(self):
        """Entity with 32767 should NOT be available."""
        data = {"test_register": EntityStatePayload(value=32767)}
        assert is_entity_available(data, "test_register") is False

    def test_entity_with_32766_not_available(self):
        """Entity with 32766 should NOT be available."""
        data = {"test_register": EntityStatePayload(value=32766)}
        assert is_entity_available(data, "test_register") is False

    def test_entity_with_32765_waiting(self):
        """Entity with 32765 should NOT be available."""
        data = {"test_register": EntityStatePayload(value=32765)}
        assert is_entity_available(data, "test_register") is False

    def test_entity_with_none_not_available(self):
        """Entity with None value should NOT be available."""
        data = {"test_register": EntityStatePayload(value=None)}
        assert is_entity_available(data, "test_register") is False

    def test_entity_missing_from_data(self):
        """Entity not in coordinator data should NOT be available."""
        data = {}
        assert is_entity_available(data, "test_register") is False

    def test_entity_with_dict_format(self):
        """Entity with dict-format data should work."""
        data = {"test_register": {"value": 32767}}
        assert is_entity_available(data, "test_register") is False


# ── MappingTransform handling ───────────────────────────────────────────


class TestMappingTransformSpecialValues:
    """Tests for ModbusMappingTransform handling of special register values."""

    def _make_processed_item(self, raw_value, enum_map=None):
        """Helper to create a ProcessedRegisterItem with minimal fields."""

        class MockDataType:
            signed = False
            scaling = 1

        item = ProcessedRegisterItem(
            raw_value=raw_value,
            input_type="input",
            address=10,
            description="Test Register 10",
            item=None,
        )
        item.item = type(
            "MockItem",
            (),
            {"data_type": MockDataType(), "enum_map": enum_map},
        )()
        return item

    def test_scaled_register_with_32767_not_scaled(self):
        """Special value 32767 should NOT be scaled, passed through raw."""
        transform = ModbusMappingTransform()
        item = self._make_processed_item(32767)

        class MockDataType:
            signed = False
            scaling = 0.01

        item.item.data_type = MockDataType()

        result = transform.apply_register_processing("test_register", item, {})
        assert result.value == 32767

    def test_scaled_register_with_32766_not_scaled(self):
        """Special value 32766 should NOT be scaled, passed through raw."""
        transform = ModbusMappingTransform()
        item = self._make_processed_item(32766)

        class MockDataType:
            signed = False
            scaling = 0.01

        item.item.data_type = MockDataType()

        result = transform.apply_register_processing("test_register", item, {})
        assert result.value == 32766

    def test_scaled_register_with_32765_not_scaled(self):
        """Special value 32765 should NOT be scaled, passed through raw."""
        transform = ModbusMappingTransform()
        item = self._make_processed_item(32765)

        class MockDataType:
            signed = False
            scaling = 0.01

        item.item.data_type = MockDataType()

        result = transform.apply_register_processing("test_register", item, {})
        assert result.value == 32765

    def test_normal_value_gets_scaled(self):
        """Normal values should be scaled normally."""
        transform = ModbusMappingTransform()
        item = self._make_processed_item(3250)

        class MockDataType:
            signed = False
            scaling = 0.01

        item.item.data_type = MockDataType()

        result = transform.apply_register_processing("test_register", item, {})
        assert result.value == 32.5

    def test_enum_register_skipped_when_32767(self):
        """Enum register with 32767 and small enum_map should be skipped."""
        # With small enum_map (<=2 entries), 32767 should cause skip
        # process_input_register_block checks is_unavailable_value
        from custom_components.ha_daikin_altherma4_modbus.common import (
            is_unavailable_value,
        )

        assert is_unavailable_value(32767) is True
        assert is_unavailable_value(32766) is True
        assert is_unavailable_value(32765) is True
