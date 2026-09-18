"""Availability tests for coil switches (Silver entity-unavailable).

``DaikinCoilSwitch`` needs no Home Assistant instance: ``CoordinatorEntity``
only stores the coordinator, so a ``SimpleNamespace`` stand-in is enough to
exercise the ``available`` property against real production code.
"""

from types import SimpleNamespace

from custom_components.ha_daikin_altherma4_modbus.entities.switch import (
    DaikinCoilSwitch,
)


def _make_switch(data):
    coordinator = SimpleNamespace(data=data)
    entry = SimpleNamespace(entry_id="test")
    return DaikinCoilSwitch(
        coordinator,
        entry,
        address=1,
        register_name="coil_1",
        translation_key="test_coil",
    )


def test_coil_switch_available_with_valid_value():
    assert _make_switch({"coil_1": {"value": 1}}).available is True


def test_coil_switch_unavailable_without_data():
    assert _make_switch({}).available is False


def test_coil_switch_unavailable_on_unsupported_register():
    assert _make_switch({"coil_1": {"value": 32767}}).available is False
