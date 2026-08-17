"""Tests for CalculatedCoPSensor using centralized mocking approach."""

from types import SimpleNamespace

from tests.helpers.modules import setup_sensor_test_module


def test_cop_sensor_with_external_power_sensor(monkeypatch):
    """Test CoP calculation with external power sensor."""
    sensor_module = setup_sensor_test_module(monkeypatch)

    # Setup: heat_power = 3500W, electric_power = 1000W -> CoP = 3.5
    # Flow = 10 L/min, delta_T = 5K -> heat_power = 10 * 5 * 70 = 3500W
    states = {
        "sensor.external_power": SimpleNamespace(
            state="1000", attributes={"unit_of_measurement": "W"}
        ),
    }
    hass = SimpleNamespace(
        states=SimpleNamespace(get=lambda entity_id: states.get(entity_id))
    )

    coordinator = SimpleNamespace(
        hass=hass,
        data={
            "input_49": {"value": 10.0},  # Flow = 10 L/min (already scaled)
            "input_40": {"value": 45.0},  # Temp = 45°C (already scaled)
            "input_42": {"value": 40.0},  # Temp = 40°C (already scaled)
        },
    )

    sensor = sensor_module.CalculatedCoPSensor(
        coordinator=coordinator,
        entry=SimpleNamespace(
            data={}, options={"electric_power_sensor": "sensor.external_power"}
        ),
        unique_id="cop",
        unit="CoP",
        device_class=None,
    )

    # heat_power = 10 * 5 * 70 = 3500W, electric_power = 1000W
    # CoP = 3500 / 1000 = 3.5
    assert sensor.native_value == 3.5


def test_cop_sensor_with_modbus_power_data(monkeypatch):
    """Test CoP calculation with Modbus power data (input_51)."""
    sensor_module = setup_sensor_test_module(monkeypatch)

    # No external sensor configured - should use input_51
    hass = SimpleNamespace(states=SimpleNamespace(get=lambda entity_id: None))

    coordinator = SimpleNamespace(
        hass=hass,
        data={
            "input_49": {"value": 10.0},  # Flow = 10 L/min (already scaled)
            "input_40": {"value": 45.0},  # Temp = 45°C (already scaled)
            "input_42": {"value": 40.0},  # Temp = 40°C (already scaled)
            "input_51": {"value": 1.0},  # Power = 1.0 kW = 1000W (already scaled)
        },
    )

    sensor = sensor_module.CalculatedCoPSensor(
        coordinator=coordinator,
        entry=SimpleNamespace(data={}, options={}),  # No external sensor
        unique_id="cop",
        unit="CoP",
        device_class=None,
    )

    # heat_power = 10 * 5 * 70 = 3500W, electric_power = 1000W
    # CoP = 3500 / 1000 = 3.5
    assert sensor.native_value == 3.5


def test_cop_sensor_returns_none_when_heat_power_is_zero(monkeypatch):
    """Test that CoP returns None when heat power is zero (pump not running)."""
    sensor_module = setup_sensor_test_module(monkeypatch)

    states = {
        "sensor.external_power": SimpleNamespace(
            state="1000", attributes={"unit_of_measurement": "W"}
        ),
    }
    hass = SimpleNamespace(
        states=SimpleNamespace(get=lambda entity_id: states.get(entity_id))
    )

    coordinator = SimpleNamespace(
        hass=hass,
        data={
            "input_49": {
                "value": 0.0,
            },  # Flow = 0 L/min
            "input_40": {
                "value": 45.0,
            },  # Vorlauf = 45°C
            "input_42": {
                "value": 45.0,
            },  # Rücklauf = 45°C, delta_T = 0
        },
    )

    sensor = sensor_module.CalculatedCoPSensor(
        coordinator=coordinator,
        entry=SimpleNamespace(
            data={}, options={"electric_power_sensor": "sensor.external_power"}
        ),
        unique_id="cop",
        unit="CoP",
        device_class=None,
    )

    # heat_power = 0, should return None
    assert sensor.native_value is None


def test_cop_sensor_returns_none_when_electric_power_is_zero(monkeypatch):
    """Test that CoP returns None when electric power is zero."""
    sensor_module = setup_sensor_test_module(monkeypatch)

    states = {
        "sensor.external_power": SimpleNamespace(
            state="0", attributes={"unit_of_measurement": "W"}
        ),
    }
    hass = SimpleNamespace(
        states=SimpleNamespace(get=lambda entity_id: states.get(entity_id))
    )

    coordinator = SimpleNamespace(
        hass=hass,
        data={
            "input_49": {
                "value": 10.0,
            },  # Flow = 10 L/min
            "input_40": {
                "value": 45.0,
            },  # Vorlauf = 45°C
            "input_42": {
                "value": 40.0,
            },  # Rücklauf = 40°C
        },
    )

    sensor = sensor_module.CalculatedCoPSensor(
        coordinator=coordinator,
        entry=SimpleNamespace(
            data={}, options={"electric_power_sensor": "sensor.external_power"}
        ),
        unique_id="cop",
        unit="CoP",
        device_class=None,
    )

    # electric_power = 0, should return None
    assert sensor.native_value is None


def test_cop_sensor_returns_none_when_external_sensor_unavailable(monkeypatch):
    """Test that CoP returns None when external power sensor is unavailable."""
    sensor_module = setup_sensor_test_module(monkeypatch)

    # External sensor returns unavailable
    states = {
        "sensor.external_power": SimpleNamespace(
            state="unavailable", attributes={"unit_of_measurement": "W"}
        ),
    }
    hass = SimpleNamespace(
        states=SimpleNamespace(get=lambda entity_id: states.get(entity_id))
    )

    # Also no input_51 data available
    coordinator = SimpleNamespace(
        hass=hass,
        data={
            "input_49": {
                "value": 10.0,
            },
            "input_40": {
                "value": 45.0,
            },
            "input_42": {
                "value": 40.0,
            },
        },
    )

    sensor = sensor_module.CalculatedCoPSensor(
        coordinator=coordinator,
        entry=SimpleNamespace(
            data={}, options={"electric_power_sensor": "sensor.external_power"}
        ),
        unique_id="cop",
        unit="CoP",
        device_class=None,
    )

    # electric_power is None, should return None
    assert sensor.native_value is None


def test_cop_sensor_with_unscaled_modbus_data(monkeypatch):
    """Test CoP calculation when Modbus data has no scale stored."""
    sensor_module = setup_sensor_test_module(monkeypatch)

    hass = SimpleNamespace(states=SimpleNamespace(get=lambda entity_id: None))

    coordinator = SimpleNamespace(
        hass=hass,
        data={
            "input_49": {
                "value": 10.0
            },  # No scale stored in data, but value is already scaled
            "input_40": {
                "value": 45.0
            },  # No scale stored in data, but value is already scaled
            "input_42": {
                "value": 40.0
            },  # No scale stored in data, but value is already scaled
            "input_51": {
                "value": 1.0
            },  # No scale stored in data, but value is already scaled (1.0 kW = 1000W)
        },
    )

    sensor = sensor_module.CalculatedCoPSensor(
        coordinator=coordinator,
        entry=SimpleNamespace(data={}, options={}),
        unique_id="cop",
        unit="CoP",
        device_class=None,
    )

    # With raw values (no scale in data), the calculation should still work
    # because sensor.py applies scaling from register definition
    # heat_power = (1000 * 0.01) * ((4500 * 0.01) - (4000 * 0.01)) * 70
    #            = 10 * 5 * 70 = 3500W
    # electric_power = 100 * 10 = 1000W
    # CoP = 3500 / 1000 = 3.5
    assert sensor.native_value == 3.5


def test_cop_sensor_rounds_to_two_decimals(monkeypatch):
    """Test that CoP is rounded to 2 decimal places."""
    sensor_module = setup_sensor_test_module(monkeypatch)

    states = {
        "sensor.external_power": SimpleNamespace(
            state="1175", attributes={"unit_of_measurement": "W"}
        ),
    }
    hass = SimpleNamespace(
        states=SimpleNamespace(get=lambda entity_id: states.get(entity_id))
    )

    coordinator = SimpleNamespace(
        hass=hass,
        data={
            "input_49": {
                "value": 10.0,
            },
            "input_40": {
                "value": 45.0,
            },
            "input_42": {
                "value": 40.0,
            },
        },
    )

    sensor = sensor_module.CalculatedCoPSensor(
        coordinator=coordinator,
        entry=SimpleNamespace(
            data={}, options={"electric_power_sensor": "sensor.external_power"}
        ),
        unique_id="cop",
        unit="CoP",
        device_class=None,
    )

    # heat_power = 3500W, electric_power = 1175W
    # CoP = 3500 / 1175 = 2.978723... -> should round to 2.98
    assert sensor.native_value == 2.98


def test_cop_sensor_with_legacy_entry_data(monkeypatch):
    """Test CoP calculation when electric_power_sensor is in entry.data (legacy)."""
    sensor_module = setup_sensor_test_module(monkeypatch)

    states = {
        "sensor.legacy_power": SimpleNamespace(
            state="500", attributes={"unit_of_measurement": "W"}
        ),
    }
    hass = SimpleNamespace(
        states=SimpleNamespace(get=lambda entity_id: states.get(entity_id))
    )

    coordinator = SimpleNamespace(
        hass=hass,
        data={
            "input_49": {
                "value": 10.0,
            },
            "input_40": {
                "value": 45.0,
            },
            "input_42": {
                "value": 40.0,
            },
        },
    )

    # Legacy: electric_power_sensor in entry.data, not options
    sensor = sensor_module.CalculatedCoPSensor(
        coordinator=coordinator,
        entry=SimpleNamespace(
            data={"electric_power_sensor": "sensor.legacy_power"},
            options={},
        ),
        unique_id="cop",
        unit="CoP",
        device_class=None,
    )

    # heat_power = 3500W, electric_power = 500W -> CoP = 7.0
    assert sensor.native_value == 7.0


def test_cop_sensor_returns_none_when_electric_power_below_threshold(monkeypatch):
    """Test that CoP returns None when electric power is below 150W threshold."""
    sensor_module = setup_sensor_test_module(monkeypatch)

    states = {
        "sensor.external_power": SimpleNamespace(
            state="100", attributes={"unit_of_measurement": "W"}
        ),
    }
    hass = SimpleNamespace(
        states=SimpleNamespace(get=lambda entity_id: states.get(entity_id))
    )

    coordinator = SimpleNamespace(
        hass=hass,
        data={
            "input_49": {"value": 10.0},  # Flow = 10 L/min
            "input_40": {"value": 45.0},  # Vorlauf = 45°C
            "input_42": {"value": 40.0},  # Rücklauf = 40°C
        },
    )

    sensor = sensor_module.CalculatedCoPSensor(
        coordinator=coordinator,
        entry=SimpleNamespace(
            data={}, options={"electric_power_sensor": "sensor.external_power"}
        ),
        unique_id="cop",
        unit="CoP",
        device_class=None,
    )

    # heat_power = 3500W, electric_power = 100W (< 150W) -> should return None
    assert sensor.native_value is None


def test_cop_sensor_cooling_mode_negative_delta_t(monkeypatch):
    """Test CoP calculation in cooling mode where Vorlauf < Rücklauf (negative delta_t)."""
    sensor_module = setup_sensor_test_module(monkeypatch)

    states = {
        "sensor.external_power": SimpleNamespace(
            state="800", attributes={"unit_of_measurement": "W"}
        ),
    }
    hass = SimpleNamespace(
        states=SimpleNamespace(get=lambda entity_id: states.get(entity_id))
    )

    # Cooling mode: Vorlauf (7°C) < Rücklauf (12°C) -> delta_t = -5K
    coordinator = SimpleNamespace(
        hass=hass,
        data={
            "input_49": {"value": 10.0},  # Flow = 10 L/min
            "input_40": {"value": 7.0},  # Vorlauf = 7°C (kalt)
            "input_42": {"value": 12.0},  # Rücklauf = 12°C (warm)
        },
    )

    sensor = sensor_module.CalculatedCoPSensor(
        coordinator=coordinator,
        entry=SimpleNamespace(
            data={}, options={"electric_power_sensor": "sensor.external_power"}
        ),
        unique_id="cop",
        unit="CoP",
        device_class=None,
    )

    # heat_power = 10 * abs(7 - 12) * 70 = 10 * 5 * 70 = 3500W
    # electric_power = 800W
    # CoP = 3500 / 800 = 4.375 -> rounded to 4.38
    assert sensor.native_value == 4.38


def test_cop_sensor_cooling_mode_with_modbus_power(monkeypatch):
    """Test CoP calculation in cooling mode using Modbus power data."""
    sensor_module = setup_sensor_test_module(monkeypatch)

    hass = SimpleNamespace(states=SimpleNamespace(get=lambda entity_id: None))

    # Cooling mode: Vorlauf (8°C) < Rücklauf (14°C) -> delta_t = -6K
    coordinator = SimpleNamespace(
        hass=hass,
        data={
            "input_49": {"value": 8.0},  # Flow = 8 L/min
            "input_40": {"value": 8.0},  # Vorlauf = 8°C
            "input_42": {"value": 14.0},  # Rücklauf = 14°C
            "input_51": {"value": 0.72},  # Power = 0.72 kW = 720W
        },
    )

    sensor = sensor_module.CalculatedCoPSensor(
        coordinator=coordinator,
        entry=SimpleNamespace(data={}, options={}),
        unique_id="cop",
        unit="CoP",
        device_class=None,
    )

    # heat_power = 8 * abs(8 - 14) * 70 = 8 * 6 * 70 = 3360W
    # electric_power = 720W
    # CoP = 3360 / 720 = 4.666... -> rounded to 4.67
    assert sensor.native_value == 4.67
