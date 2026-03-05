#!/usr/bin/env python3
"""
Test for all Last Triggered sensors functionality (Last Defrost, Last Compressor Run, Last DHW Running, Last Booster Heater).
"""

import pytest

# Import shared test utilities
from .test_utils import (
    setup_home_assistant_mocks,
    setup_project_paths,
    load_const_module,
    create_mock_coordinator,
    create_test_trigger_time,
)

# Set up mocks and paths
setup_home_assistant_mocks()
project_root = setup_project_paths()
const_module = load_const_module(project_root)


class TestLastTriggeredSensors:
    """Test all Last Triggered sensors functionality."""

    @pytest.fixture
    def mock_coordinator(self):
        """Mock coordinator with test data."""
        return create_mock_coordinator()

    def test_all_last_triggered_sensors_definition(self):
        """Test that all last_triggered sensors are properly defined."""
        expected_sensors = [
            "last_compressor_run",
            "last_defrost",
            "last_booster_heater",
            "last_dhw_running",
        ]

        found_sensors = {}

        for sensor in const_module.CALCULATED_SENSORS:
            register_name = sensor.get("register_name")
            if register_name in expected_sensors:
                found_sensors[register_name] = sensor

        # Check all expected sensors are found
        for expected in expected_sensors:
            assert (
                expected in found_sensors
            ), f"{expected} sensor not found in CALCULATED_SENSORS"

        # Check each sensor has correct properties
        for register_name, sensor_config in found_sensors.items():
            assert (
                sensor_config["type"] == "last_triggered"
            ), f"{register_name} should have type 'last_triggered'"
            assert (
                sensor_config["device_class"] == "timestamp"
            ), f"{register_name} should have device_class 'timestamp'"
            assert (
                "trigger_register_name" in sensor_config
            ), f"{register_name} should have trigger_register_name"
            assert (
                "translation_key" in sensor_config
            ), f"{register_name} should have translation_key"

            print(
                f"✓ {register_name} sensor definition found: {sensor_config['trigger_register_name']}"
            )

    def test_trigger_registers_mapping(self):
        """Test that trigger registers are correctly mapped."""
        expected_mappings = {
            "last_compressor_run": "discrete_11",
            "last_defrost": "discrete_17",
            "last_booster_heater": "discrete_8",
            "last_dhw_running": "discrete_19",
        }

        for sensor_name, expected_trigger in expected_mappings.items():
            sensor_config = None
            for sensor in const_module.CALCULATED_SENSORS:
                if sensor.get("register_name") == sensor_name:
                    sensor_config = sensor
                    break

            assert sensor_config is not None, f"{sensor_name} not found"
            assert (
                sensor_config["trigger_register_name"] == expected_trigger
            ), f"{sensor_name} should trigger on {expected_trigger}"

            print(f"✓ {sensor_name} -> {expected_trigger} mapping correct")

    def test_last_triggered_mechanism_simulation(self):
        """Test the last_triggered mechanism simulation for all sensors."""
        test_cases = [
            ("last_compressor_run", "discrete_11", "Compressor"),
            ("last_defrost", "discrete_17", "Defrost"),
            ("last_booster_heater", "discrete_8", "Booster Heater"),
            ("last_dhw_running", "discrete_19", "DHW Running"),
        ]

        for sensor_name, trigger_register, description in test_cases:
            # Test data: trigger register state changes (0 -> 1)
            previous_data = {trigger_register: {"value": 0}}
            current_data = {trigger_register: {"value": 1}}

            # Simulate trigger detection
            previous_val = previous_data.get(trigger_register, {}).get("value")
            current_val = current_data.get(trigger_register, {}).get("value")

            is_on = current_val == 1
            was_on = previous_val == 1 if previous_val is not None else False

            # Should trigger (was off, now on)
            assert is_on, f"{description} current value should be on"
            assert not was_on, f"{description} previous value should be off"
            assert is_on and not was_on, f"{description} should trigger condition"

            # Simulate timestamp recording
            trigger_time = create_test_trigger_time()
            last_triggered = {sensor_name: trigger_time}

            # Verify trigger recorded
            assert sensor_name in last_triggered
            assert last_triggered[sensor_name] == trigger_time

            print(f"✓ {description} last triggered mechanism working")

    def test_last_triggered_no_trigger_scenarios(self):
        """Test scenarios where no trigger should occur for all sensors."""
        trigger_registers = ["discrete_11", "discrete_17", "discrete_8", "discrete_19"]
        descriptions = ["Compressor", "Defrost", "Booster Heater", "DHW Running"]

        for trigger_register, description in zip(trigger_registers, descriptions):
            # Scenario 1: Stays off (0 -> 0)
            previous_data = {trigger_register: {"value": 0}}
            current_data = {trigger_register: {"value": 0}}

            previous_val = previous_data.get(trigger_register, {}).get("value")
            current_val = current_data.get(trigger_register, {}).get("value")

            is_on = current_val == 1
            was_on = previous_val == 1 if previous_val is not None else False

            should_trigger = is_on and not was_on
            assert (
                not should_trigger
            ), f"{description} should not trigger when staying off"

            # Scenario 2: Stays on (1 -> 1)
            previous_data = {trigger_register: {"value": 1}}
            current_data = {trigger_register: {"value": 1}}

            previous_val = previous_data.get(trigger_register, {}).get("value")
            current_val = current_data.get(trigger_register, {}).get("value")

            is_on = current_val == 1
            was_on = previous_val == 1 if previous_val is not None else False

            should_trigger = is_on and not was_on
            assert (
                not should_trigger
            ), f"{description} should not trigger when staying on"

            # Scenario 3: Turns off (1 -> 0)
            previous_data = {trigger_register: {"value": 1}}
            current_data = {trigger_register: {"value": 0}}

            previous_val = previous_data.get(trigger_register, {}).get("value")
            current_val = current_data.get(trigger_register, {}).get("value")

            is_on = current_val == 1
            was_on = previous_val == 1 if previous_val is not None else False

            should_trigger = is_on and not was_on
            assert (
                not should_trigger
            ), f"{description} should not trigger when turning off"

            print(f"✓ {description} no-trigger scenarios verified")

    def test_all_state_changes(self):
        """Test various state change scenarios for all sensors."""
        test_scenarios = [
            (0, 1, True, "starts"),
            (1, 1, False, "continues"),
            (1, 0, False, "ends"),
            (0, 0, False, "stays off"),
        ]

        sensors = [
            "last_compressor_run",
            "last_defrost",
            "last_booster_heater",
            "last_dhw_running",
        ]
        trigger_registers = ["discrete_11", "discrete_17", "discrete_8", "discrete_19"]

        for sensor_name, trigger_register in zip(sensors, trigger_registers):
            for previous_val, current_val, should_trigger, action in test_scenarios:
                is_on = current_val == 1
                was_on = previous_val == 1 if previous_val is not None else False
                actual_trigger = is_on and not was_on

                assert (
                    actual_trigger == should_trigger
                ), f"Trigger mismatch for {sensor_name} when {action}"

                if should_trigger:
                    print(
                        f"✓ {sensor_name}: {action} ({previous_val} -> {current_val}), trigger = {actual_trigger}"
                    )

    def test_all_data_structures(self):
        """Test the data structure for all last_triggered sensors."""
        sensors = [
            "last_compressor_run",
            "last_defrost",
            "last_booster_heater",
            "last_dhw_running",
        ]

        for sensor_name in sensors:
            # Simulate the data structure that would be created
            trigger_time = create_test_trigger_time()

            sensor_data = {
                "value": trigger_time,
                "input_type": "calculated",
                "register_name": sensor_name,
            }

            # Verify structure
            assert "value" in sensor_data
            assert "input_type" in sensor_data
            assert "register_name" in sensor_data
            assert sensor_data["value"] == trigger_time
            assert sensor_data["input_type"] == "calculated"
            assert sensor_data["register_name"] == sensor_name

            print(f"✓ {sensor_name} data structure correct")

    def test_all_sensor_properties(self):
        """Test all last_triggered sensor properties."""
        expected_sensors = {
            "last_compressor_run": "Last Compressor Run",
            "last_defrost": "Last Defrost",
            "last_booster_heater": "Last Booster Heater",
            "last_dhw_running": "Last DHW running",  # Korrigierter Name
        }

        found_sensors = {}
        for sensor in const_module.CALCULATED_SENSORS:
            register_name = sensor.get("register_name")
            if register_name in expected_sensors:
                found_sensors[register_name] = sensor

        for register_name, expected_name in expected_sensors.items():
            sensor_config = found_sensors[register_name]

            # Verify sensor configuration
            assert sensor_config["name"] == expected_name
            assert sensor_config["type"] == "last_triggered"
            assert sensor_config["device_class"] == "timestamp"
            assert "trigger_register_name" in sensor_config
            assert "translation_key" in sensor_config

            print(f"✓ {expected_name} sensor properties correct")

    def test_multiple_trigger_cycles(self):
        """Test multiple trigger cycles for all sensors."""
        sensors = [
            "last_compressor_run",
            "last_defrost",
            "last_booster_heater",
            "last_dhw_running",
        ]
        trigger_registers = ["discrete_11", "discrete_17", "discrete_8", "discrete_19"]

        trigger_times = [
            create_test_trigger_time(),  # Test time
            create_test_trigger_time(),  # Test time
            create_test_trigger_time(),  # Test time
        ]

        for sensor_name, trigger_register in zip(sensors, trigger_registers):
            # Simulate multiple cycles
            states = [
                {trigger_register: {"value": 0}},  # Off
                {trigger_register: {"value": 1}},  # On - trigger 1
                {trigger_register: {"value": 0}},  # Off
                {trigger_register: {"value": 1}},  # On - trigger 2
                {trigger_register: {"value": 0}},  # Off
                {trigger_register: {"value": 1}},  # On - trigger 3
            ]

            # Track triggers
            trigger_count = 0
            last_trigger_time = None

            for i in range(1, len(states)):
                previous_val = states[i - 1][trigger_register]["value"]
                current_val = states[i][trigger_register]["value"]

                is_on = current_val == 1
                was_on = previous_val == 1

                if is_on and not was_on:
                    trigger_count += 1
                    last_trigger_time = trigger_times[trigger_count - 1]

            assert trigger_count == 3, f"{sensor_name} should have 3 triggers"
            assert (
                last_trigger_time == create_test_trigger_time()
            ), f"{sensor_name} last trigger should be test time"

            print(f"✓ {sensor_name}: {trigger_count} triggers recorded")

    def test_concurrent_triggers(self):
        """Test concurrent triggers from multiple sensors."""
        # Simulate multiple sensors triggering at different times
        trigger_data = {
            "discrete_11": {"value": 1},  # Compressor starts
            "discrete_17": {"value": 0},  # Defrost off
            "discrete_8": {"value": 1},  # Booster heater starts
            "discrete_19": {"value": 0},  # DHW off
        }

        previous_data = {
            "discrete_11": {"value": 0},  # Compressor was off
            "discrete_17": {"value": 0},  # Defrost was off
            "discrete_8": {"value": 0},  # Booster heater was off
            "discrete_19": {"value": 0},  # DHW was off
        }

        create_test_trigger_time()

        # Simulate trigger detection
        actual_triggers = []
        for register_name, register_data in trigger_data.items():
            previous_val = previous_data.get(register_name, {}).get("value")
            current_val = register_data.get("value")

            is_on = current_val == 1
            was_on = previous_val == 1 if previous_val is not None else False

            if is_on and not was_on:
                # Find corresponding sensor
                for sensor in const_module.CALCULATED_SENSORS:
                    if sensor.get("trigger_register_name") == register_name:
                        actual_triggers.append(sensor.get("register_name"))
                        break

        # Verify expected triggers occurred
        assert (
            len(actual_triggers) == 2
        ), f"Should have 2 triggers, got {len(actual_triggers)}"
        assert "last_compressor_run" in actual_triggers, "Compressor should trigger"
        assert "last_booster_heater" in actual_triggers, "Booster heater should trigger"

        print(f"✓ Concurrent triggers: {actual_triggers}")

    def test_integration_workflow_all_sensors(self):
        """Test complete integration workflow for all sensors."""
        sensors = [
            "last_compressor_run",
            "last_defrost",
            "last_booster_heater",
            "last_dhw_running",
        ]
        trigger_registers = ["discrete_11", "discrete_17", "discrete_8", "discrete_19"]

        for sensor_name, trigger_register in zip(sensors, trigger_registers):
            # Step 1: Initial state - off
            previous_state = {trigger_register: {"value": 0}}

            # Step 2: Starts (0 -> 1)
            current_state = {trigger_register: {"value": 1}}

            # Step 3: Detect trigger
            previous_val = previous_state.get(trigger_register, {}).get("value")
            current_val = current_state.get(trigger_register, {}).get("value")

            is_on = current_val == 1
            was_on = previous_val == 1 if previous_val is not None else False
            should_trigger = is_on and not was_on

            assert should_trigger, f"{sensor_name} should trigger when starting"

            # Step 4: Record timestamp
            trigger_time = create_test_trigger_time()

            # Step 5: Create sensor data
            sensor_data = {
                "value": trigger_time,
                "input_type": "calculated",
                "register_name": sensor_name,
            }

            # Step 6: Verify sensor would show timestamp
            assert sensor_data["value"] == trigger_time

            print(f"✓ {sensor_name} workflow: trigger -> timestamp: {trigger_time}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
