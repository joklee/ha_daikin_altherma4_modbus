"""Entity-level tests for central SPECIAL_REGISTER_VALUES handling.

Covers the reported bug: DHW thermostat showed a 32766 setpoint and a
44.5 °C value. mapping_transform keeps specials raw (never 327.66);
helpers detect raw AND scaled guards; entities return None/unavailable
instead of leaking markers. Select exception: 32766 in enum_map stays
valid (holding_80 = off).
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock

from custom_components.ha_daikin_altherma4_modbus.core.data_types import (
    ProcessedRegisterItem,
)
from custom_components.ha_daikin_altherma4_modbus.core.mapping_transform import (
    ModbusMappingTransform,
)
from custom_components.ha_daikin_altherma4_modbus.core.register_types import TEMP16
from custom_components.ha_daikin_altherma4_modbus.entities.climate import (
    DaikinDHWThermostat,
    DaikinThermostatClimate,
)
from custom_components.ha_daikin_altherma4_modbus.entities.number import DaikinNumber
from custom_components.ha_daikin_altherma4_modbus.entities.select import DaikinSelect
from custom_components.ha_daikin_altherma4_modbus.entities.sensor import (
    DaikinInputSensor,
)
from custom_components.ha_daikin_altherma4_modbus.entities.switch import (
    DaikinHoldingSwitch,
)


def _coord(data):
    return SimpleNamespace(
        data=data,
        data_manager=SimpleNamespace(
            write_holding_register=AsyncMock(),
            write_coil_register=AsyncMock(),
        ),
    )


def _number(register_name, value, scale=0.01):
    coord = _coord({register_name: {"value": value, "scale": scale}})
    return DaikinNumber(
        coord,
        SimpleNamespace(entry_id="test"),
        76,
        12,
        30,
        1,
        "°C",
        TEMP16,
        register_name,
    )


def _sensor(register_name, value):
    coord = _coord({register_name: {"value": value, "scale": 0.01}})
    return DaikinInputSensor(
        coord,
        SimpleNamespace(entry_id="test"),
        43,
        "°C",
        TEMP16,
        1,
        None,
        register_name,
        device_class="temperature",
        unique_id=f"test_{register_name}",
    )


# ── mapping_transform: specials never scaled ──────────────────────────


class TestMappingNeverScalesSpecials:
    def _item(self, raw):
        holder = SimpleNamespace(data_type=TEMP16, enum_map=None)
        return ProcessedRegisterItem(
            raw_value=raw,
            input_type="holding",
            address=76,
            description="test",
            item=holder,
        )

    def test_raw_special_stays_raw(self):
        out = ModbusMappingTransform.apply_register_processing(
            "holding_76", self._item(32766), {}
        )
        assert out.value == 32766  # never 327.66

    def test_normal_value_scaled(self):
        out = ModbusMappingTransform.apply_register_processing(
            "holding_76", self._item(2100), {}
        )
        assert out.value == 21.0


# ── number ────────────────────────────────────────────────────────────


class TestNumberSpecials:
    def test_raw_special_is_none_and_unavailable(self):
        ent = _number("holding_76", 32766)
        assert ent.native_value is None
        assert ent.available is False

    def test_scaled_guard_is_none_and_unavailable(self):
        ent = _number("holding_76", 327.66)
        assert ent.native_value is None
        assert ent.available is False

    def test_normal_scaled_value_passes_through(self):
        ent = _number("holding_76", 21.0)
        assert ent.native_value == 21.0
        assert ent.available is True


# ── sensor (check runs BEFORE float conversion) ───────────────────────


class TestSensorSpecials:
    def test_scaled_guard_is_none(self):
        assert _sensor("input_43", 327.66).native_value is None

    def test_raw_special_is_none(self):
        assert _sensor("input_43", 32766).native_value is None

    def test_normal_value(self):
        assert _sensor("input_43", 44.5).native_value == 44.5


# ── select exception: 32766 can be a valid option ─────────────────────


def _select(value):
    coord = _coord({"holding_80": {"value": value, "scale": 1}})
    enum_map = {0: "reheat", 1: "schedule_and_reheat", 2: "scheduled", 32766: "off"}
    return DaikinSelect(
        coord, SimpleNamespace(entry_id="test"), 80, "holding_80", enum_map
    )


class TestSelectSpecials:
    def test_enum_mapped_special_stays_available(self):
        ent = _select(32766)
        assert ent.available is True
        assert ent.current_option == "off"

    def test_unsupported_special_is_unavailable(self):
        ent = _select(32767)
        assert ent.available is False
        assert ent.current_option is None

    def test_normal_option(self):
        ent = _select(0)
        assert ent.available is True
        assert ent.current_option == "reheat"


# ── switch ────────────────────────────────────────────────────────────


class TestHoldingSwitchSpecials:
    def _switch(self, value):
        coord = _coord({"holding_13": {"value": value, "scale": 1}})
        return DaikinHoldingSwitch(
            coord,
            SimpleNamespace(entry_id="test"),
            13,
            "holding_13",
            translation_key="holding_13",
            enum_map={0: "off", 1: "on_powerful"},
        )

    def test_special_is_unavailable(self):
        assert self._switch(32766).available is False

    def test_normal_is_available(self):
        assert self._switch(1).available is True


# ── reported bug: DHW thermostat 32766 setpoint + 44.5 °C ─────────────


def _dhw_manual(holding_10, input_43):
    coord = _coord(
        {
            "holding_10": {"value": holding_10, "scale": 1},
            "input_43": {"value": input_43, "scale": 0.01},
            "coil_1": {"value": True, "scale": 1},
            "discrete_19": {"value": True, "scale": 1},
        }
    )
    ent = DaikinDHWThermostat.__new__(DaikinDHWThermostat)
    ent.coordinator = coord
    ent._entry = SimpleNamespace(entry_id="test")
    ent._dhw_type = "manual"
    ent._hvac_mode_register = "coil_1"
    ent._running_register = "discrete_19"
    ent._temp_register = "input_43"
    ent._setpoint_register = "holding_10"
    return ent


class TestDhwThermostatSpecials:
    def test_unavailable_setpoint_is_none_not_32766(self):
        ent = _dhw_manual(32766, 44.5)
        assert ent.target_temperature is None
        assert ent.current_temperature == 44.5

    def test_normal_setpoint(self):
        ent = _dhw_manual(48, 44.5)
        assert ent.target_temperature == 48


# ── main thermostat: unavailable is None, never 0 ─────────────────────


class TestMainThermostatSpecials:
    def _climate(self, input_40, holding_54=0, holding_3=1):
        coord = _coord(
            {
                "input_40": {"value": input_40, "scale": 0.01},
                "holding_3": {"value": holding_3, "scale": 1},
                "holding_54": {"value": holding_54, "scale": 1},
                "holding_55": {"value": 0, "scale": 1},
                "holding_9": {"value": 0, "scale": 1},
                "input_31": {"value": 0, "scale": 1},
            }
        )
        ent = DaikinThermostatClimate.__new__(DaikinThermostatClimate)
        ent.coordinator = coord
        ent._entry = SimpleNamespace(entry_id="test")
        return ent

    def test_unavailable_current_is_none(self):
        assert self._climate(32766).current_temperature is None

    def test_scaled_guard_current_is_none(self):
        assert self._climate(327.66).current_temperature is None

    def test_normal_current(self):
        assert self._climate(32.4).current_temperature == 32.4

    def test_unavailable_offset_gives_none_target(self):
        assert self._climate(32.4, holding_54=32766).target_temperature is None

    def test_normal_offset_gives_target(self):
        assert self._climate(32.4, holding_54=2).target_temperature == 2.0

    def test_unavailable_op_mode_falls_back_to_heating_offset(self):
        ent = self._climate(32.4, holding_54=2, holding_3=32766)
        assert ent.current_temperature == 32.4
        assert ent.target_temperature == 2.0
