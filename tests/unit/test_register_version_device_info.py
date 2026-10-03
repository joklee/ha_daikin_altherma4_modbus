"""Tests for the register-map version shown in the device info.

The ``RegisterVersionDeviceInfoMixin`` enriches the static device info of
every entity with the detected Modbus register map as ``sw_version``
(visible under Geräte-Informationen):

* "Register v2/v3" once the v2/v3 map is confirmed (MMI v2/v3),
* "Register v4" once the v4 map is confirmed (MMI v4.x),
* "Register unbekannt" while the map is still unknown (fallback).
"""

from __future__ import annotations

from types import SimpleNamespace

from custom_components.ha_daikin_altherma4_modbus.common.helpers import (
    REGISTER_VERSION_UNKNOWN_LABEL,
    RegisterVersionDeviceInfoMixin,
    device_info_with_register_version,
    resolve_register_version,
)
from custom_components.ha_daikin_altherma4_modbus.core.register_constants import (
    INPUT_DEVICE_INFO,
)


class _StubEntity(RegisterVersionDeviceInfoMixin):
    """Minimal entity shape: coordinator + static device info."""

    def __init__(self, coordinator, device_info) -> None:
        self.coordinator = coordinator
        self._attr_device_info = device_info


def _coordinator_with_version(version) -> SimpleNamespace:
    data_manager = SimpleNamespace(register_version=version)
    return SimpleNamespace(data_manager=data_manager)


def test_helper_adds_detected_version_without_mutating_base() -> None:
    base = dict(INPUT_DEVICE_INFO)
    info = device_info_with_register_version(INPUT_DEVICE_INFO, "v4")
    assert info["sw_version"] == "Register v4"
    assert info["translation_key"] == INPUT_DEVICE_INFO["translation_key"]
    # The shared base dict is never mutated.
    assert "sw_version" not in INPUT_DEVICE_INFO
    assert base == INPUT_DEVICE_INFO


def test_helper_reports_unknown_label_without_version() -> None:
    assert (
        device_info_with_register_version(INPUT_DEVICE_INFO, None)["sw_version"]
        == REGISTER_VERSION_UNKNOWN_LABEL
    )
    assert REGISTER_VERSION_UNKNOWN_LABEL == "Register unbekannt"


def test_resolve_register_version_reads_data_manager() -> None:
    assert resolve_register_version(_coordinator_with_version("v2/v3")) == "v2/v3"
    assert resolve_register_version(_coordinator_with_version(None)) is None
    assert resolve_register_version(None) is None
    assert resolve_register_version(SimpleNamespace()) is None


def test_mixin_shows_detected_version_in_device_info() -> None:
    entity = _StubEntity(_coordinator_with_version("v2/v3"), INPUT_DEVICE_INFO)
    assert entity.device_info["sw_version"] == "Register v2/v3"

    entity = _StubEntity(_coordinator_with_version("v4"), INPUT_DEVICE_INFO)
    assert entity.device_info["sw_version"] == "Register v4"


def test_mixin_shows_unbekannt_while_map_unknown() -> None:
    entity = _StubEntity(_coordinator_with_version(None), INPUT_DEVICE_INFO)
    assert entity.device_info["sw_version"] == "Register unbekannt"

    entity = _StubEntity(None, INPUT_DEVICE_INFO)
    assert entity.device_info["sw_version"] == "Register unbekannt"
