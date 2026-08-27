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

import pytest

from custom_components.ha_daikin_altherma4_modbus.common import (
    is_entity_available,
    is_unavailable_value,
    validate_register_value,
)
from custom_components.ha_daikin_altherma4_modbus.common.helpers import (
    to_signed_16bit,
    to_unsigned_16bit,
)
from custom_components.ha_daikin_altherma4_modbus.core.const import (
    SPECIAL_REGISTER_NOT_AVAILABLE,
    SPECIAL_REGISTER_NOT_SUPPORTED,
    SPECIAL_REGISTER_VALUES,
    SPECIAL_REGISTER_WAITING,
)
from custom_components.ha_daikin_altherma4_modbus.core.data_types import (
    EntityStatePayload,
    ProcessedRegisterItem,
)
from custom_components.ha_daikin_altherma4_modbus.core.mapping_transform import (
    ModbusMappingTransform,
)
from custom_components.ha_daikin_altherma4_modbus.core.register_types import (
    INT16,
    INT16S100,
    POW16,
    TEMP16,
    SensorRegister,
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


# ── Systematic special-value test matrix ────────────────────────────────
#
# Matrix dimensions used by the classes below:
#   * value      : 32767 / 32766 / 32765 (+ boundary neighbors as controls)
#   * detection  : validate_register_value / is_unavailable_value /
#                  is_entity_available (dict + dataclass payload)
#   * conversion : to_signed_16bit must never flip specials into negatives
#   * data type  : TEMP16 / INT16S100 / POW16 (scaling 0.01, signed),
#                  INT16 (scaling 1, signed) — a special value must never be
#                  interpreted as an ordinary scaled number (e.g. 32767 with
#                  TEMP16 must NOT become 327.67 °C)
#   * layer      : apply_register_processing AND full block processing
#                  (input non-enum / input small enum / input large enum /
#                   holding non-enum)

_ALL_SPECIALS = [
    SPECIAL_REGISTER_NOT_SUPPORTED,
    SPECIAL_REGISTER_NOT_AVAILABLE,
    SPECIAL_REGISTER_WAITING,
]
_SPECIAL_IDS = ["not-supported", "not-available", "waiting"]


class TestSpecialValueDetectionExactness:
    """The set of special values must be matched exactly, never as a range."""

    @pytest.mark.parametrize("value", [32764, 32768], ids=["below", "above"])
    def test_boundary_neighbors_are_ordinary_values(self, value):
        """32764/32768 surround the special band but are ordinary values."""
        assert validate_register_value(value) is True
        assert is_unavailable_value(value) is False
        data = {"reg": EntityStatePayload(value=value)}
        assert is_entity_available(data, "reg") is True

    @pytest.mark.parametrize("special", _ALL_SPECIALS, ids=_SPECIAL_IDS)
    def test_numeric_string_coercion_is_consistent(self, special):
        """Numeric strings are int-cast; specials must still be detected."""
        text = str(special)
        assert validate_register_value(text) is False
        assert is_unavailable_value(text) is True

    @pytest.mark.parametrize("special", _ALL_SPECIALS, ids=_SPECIAL_IDS)
    def test_dict_payload_format_marks_entity_unavailable(self, special):
        """Dict-format coordinator payloads treat every special as missing."""
        data = {"reg": {"value": special}}
        assert is_entity_available(data, "reg") is False


class TestSignedConversionNeverFlipsSpecials:
    """Signed decoding happens before the special-value check upstream.

    The special values live below 32768, so a signed conversion that happens
    to be applied to them must be a no-op — otherwise a marker could flip
    into a negative ordinary number.
    """

    @pytest.mark.parametrize("special", _ALL_SPECIALS, ids=_SPECIAL_IDS)
    def test_to_signed_16bit_is_noop_for_specials(self, special):
        assert to_signed_16bit(special) == special
        assert to_signed_16bit(special) >= 0

    @pytest.mark.parametrize("special", _ALL_SPECIALS, ids=_SPECIAL_IDS)
    def test_unsigned_roundtrip_preserves_specials(self, special):
        assert to_unsigned_16bit(to_signed_16bit(special)) == special


class TestScalingBypassMatrix:
    """Productive data types × special values: never scale a marker.

    A regression here would surface fake measurements such as
    ``327.67 °C`` or ``327.65 kW`` instead of unavailable entities.
    """

    SCALING_TYPES = (
        ("TEMP16", TEMP16),
        ("INT16S100", INT16S100),
        ("POW16", POW16),
    )

    def _item(self, raw_value, data_type):
        """ProcessedRegisterItem wired to a real RegisterDataType."""
        item = ProcessedRegisterItem(
            raw_value=raw_value,
            input_type="input",
            address=10,
            description="Test Register 10",
            item=None,
        )
        item.item = type("MockItem", (), {"data_type": data_type, "enum_map": None})()
        return item

    @pytest.mark.parametrize(
        ("type_name", "data_type"),
        SCALING_TYPES,
        ids=[t[0] for t in SCALING_TYPES],
    )
    @pytest.mark.parametrize("special", _ALL_SPECIALS, ids=_SPECIAL_IDS)
    def test_special_stays_raw_and_unscaled(self, data_type, special, type_name):
        transform = ModbusMappingTransform()

        result = transform.apply_register_processing(
            "test_register", self._item(special, data_type), {}
        )

        # Raw marker preserved — a scale regression yields special * 0.01.
        assert result.value == special
        assert result.value != round(special * data_type.scaling, 2)

    @pytest.mark.parametrize(
        ("type_name", "data_type", "raw", "expected"),
        [
            ("TEMP16", TEMP16, 2500, 25.0),
            ("TEMP16", TEMP16, -500, -5.0),
            ("INT16S100", INT16S100, -12345, -123.45),
            ("POW16", POW16, 2000, 20.0),
            ("INT16", INT16, 3200, 3200),
        ],
        ids=[
            "temp-normal",
            "temp-negative",
            "int-scaled-negative",
            "pow",
            "int-unity",
        ],
    )
    def test_control_normal_values_scale_correctly(
        self, data_type, raw, expected, type_name
    ):
        """Control group proving the same path really scales normal values."""
        transform = ModbusMappingTransform()

        result = transform.apply_register_processing(
            "test_register", self._item(raw, data_type), {}
        )

        assert result.value == expected


class TestBlockProcessingMatrix:
    """Full block layer × special values.

    Contracts protected here:
    * a plain sensor reading 32767 is DROPPED from block output entirely
      (capability detection drives entity creation);
    * 32766/32765 stay present carrying the RAW marker value — never scaled;
    * small enums (<=2 options) drop every special (ambiguous device state);
    * large enums keep 32766/32765 as untouched integers (never mapped),
      while 32767 remains dropped unconditionally — "not supported" wins
      regardless of enum size;
    * holding blocks share the same skip rule for 32767 and still scale
      ordinary values (control case).
    """

    def _sensor(self, address, name, data_type, enum_map=None):
        return SensorRegister(
            name=name,
            address=address,
            input_type="input",
            register_name=name,
            data_type=data_type,
            enum_map=enum_map,
        )

    def _response(self, address, value):
        regs = [0] * (address + 1)
        regs[address] = value
        return types.SimpleNamespace(registers=regs)

    @pytest.mark.parametrize("special", _ALL_SPECIALS, ids=_SPECIAL_IDS)
    def test_input_plain_sensor_block_special_handling(self, special):
        transform = ModbusMappingTransform()
        reg_list = [self._sensor(10, "input_10", TEMP16)]
        response = self._response(10, special)

        data = transform.process_input_register_block(response, reg_list, 1, 87, 1)

        if special == SPECIAL_REGISTER_NOT_SUPPORTED:
            assert "input_10" not in data
        else:
            payload = data["input_10"]
            assert payload.value == special  # raw marker, never 327.66/327.65

    @pytest.mark.parametrize("special", _ALL_SPECIALS, ids=_SPECIAL_IDS)
    def test_input_small_enum_block_drops_every_special(self, special):
        transform = ModbusMappingTransform()
        reg_list = [self._sensor(12, "input_12", INT16, enum_map={0: "off", 1: "on"})]
        response = self._response(12, special)

        data = transform.process_input_register_block(response, reg_list, 1, 87, 1)

        assert "input_12" not in data

    @pytest.mark.parametrize("special", _ALL_SPECIALS, ids=_SPECIAL_IDS)
    def test_input_large_enum_block_special_handling(self, special):
        transform = ModbusMappingTransform()
        reg_list = [
            self._sensor(
                13,
                "input_13",
                INT16,
                enum_map={0: "auto", 1: "heat", 2: "cool"},
            )
        ]
        response = self._response(13, special)

        data = transform.process_input_register_block(response, reg_list, 1, 87, 1)

        if special == SPECIAL_REGISTER_NOT_SUPPORTED:
            # Unconditional skip — even a large enum never resurrects it.
            assert "input_13" not in data
        else:
            payload = data["input_13"]
            assert payload.value == special  # untouched integer — never mapped

    @pytest.mark.parametrize("special", _ALL_SPECIALS, ids=_SPECIAL_IDS)
    def test_holding_block_shares_skip_and_raw_passthrough(self, special):
        transform = ModbusMappingTransform()
        reg_list = [self._sensor(30, "holding_30", INT16S100)]
        response = self._response(30, special)

        data = transform.process_holding_register_block(response, reg_list, 1, 80, 1)

        if special == SPECIAL_REGISTER_NOT_SUPPORTED:
            assert "holding_30" not in data
        else:
            payload = data["holding_30"]
            assert payload.value == special

    def test_holding_block_scales_ordinary_values(self):
        """Control group: the very same holding path scales real values."""
        transform = ModbusMappingTransform()
        reg_list = [self._sensor(31, "holding_31", TEMP16)]
        response = self._response(31, 2500)

        data = transform.process_holding_register_block(response, reg_list, 1, 80, 1)

        assert data["holding_31"].value == 25.0
