"""services.yaml must describe every registered service.

Regression: services.yaml only defined 6 of 16 services, so the UI
showed no/wrong fields (e.g. set_dhw_single_heatup). It also listed
Smart Grid options with spaces while the schema validates
underscore names.
"""

from pathlib import Path

import yaml

from custom_components.ha_daikin_altherma4_modbus.core import const


def _load():
    path = Path("custom_components/ha_daikin_altherma4_modbus/services.yaml")
    return yaml.safe_load(path.read_text())


def _service_names():
    return {
        value
        for name, value in vars(const).items()
        if name.startswith("SERVICE_") and isinstance(value, str)
    }


def test_services_yaml_covers_all_registered_services():
    assert _service_names() == set(_load())


def test_services_yaml_requires_config_entry_id_everywhere():
    for service, definition in _load().items():
        fields = definition.get("fields", {})
        assert fields.get("config_entry_id", {}).get("required") is True, service


def test_set_dhw_single_heatup_fields():
    fields = _load()["set_dhw_single_heatup"]["fields"]
    assert fields["single_heatup"]["required"] is True
    assert fields["single_heatup"]["selector"] == {"boolean": None}
    assert fields["setpoint"]["required"] is False
    assert fields["setpoint"]["selector"]["number"]["min"] == 30
    assert fields["setpoint"]["selector"]["number"]["max"] == 85
    assert "target_temperature" not in fields


def test_start_dhw_single_heatup_fields():
    fields = _load()["start_dhw_single_heatup"]["fields"]
    assert fields["target_temperature"]["required"] is True
    assert fields["target_temperature"]["selector"]["number"]["min"] == 30
    assert fields["target_temperature"]["selector"]["number"]["max"] == 85
    assert "single_heatup" not in fields
    assert "timeout" in fields
    assert "hysteresis" in fields


def test_select_options_match_schema_names():
    services = _load()
    smart_grid = services["set_smart_grid_mode"]["fields"]["smart_grid_mode"]
    assert smart_grid["selector"]["select"]["options"] == [
        "free_running",
        "forced_off",
        "recommended_on",
        "forced_on",
    ]
    quiet = services["set_quiet_mode"]["fields"]["quiet_mode"]
    assert quiet["selector"]["select"]["options"] == [
        "off",
        "on_automatic",
        "on_manual",
    ]
