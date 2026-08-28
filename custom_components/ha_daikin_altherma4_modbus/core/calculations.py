"""Pure business logic calculations for Daikin Altherma 4 integration."""

import logging
from typing import Any

from .register_constants import (
    REGISTER_FLOW_RATE,
    REGISTER_HEAT_PUMP_POWER,
    REGISTER_LEAVING_WATER_TEMP,
    REGISTER_RETURN_WATER_TEMP,
)

_LOGGER = logging.getLogger(__name__)


def calculate_thermal_heat_output(data: dict[str, Any]) -> float:
    """Calculate thermal heat output in watts.

    Args:
        data: Dictionary containing register data with keys like 'input_49', 'input_40', etc.

    Returns:m
        Thermal heat output in watts, rounded to 2 decimal places.
    """
    # Flow rate in L/min (input_49)
    flow_data = data.get(REGISTER_FLOW_RATE, {})
    flow_raw = flow_data.get("value") if flow_data else 0

    # Leaving water temperature in °C (input_40)
    temp_vl_data = data.get(REGISTER_LEAVING_WATER_TEMP, {})
    temp_vl_raw = temp_vl_data.get("value") if temp_vl_data else 0

    # Return water temperature in °C (input_42)
    temp_rl_data = data.get(REGISTER_RETURN_WATER_TEMP, {})
    temp_rl_raw = temp_rl_data.get("value") if temp_rl_data else 0

    # Values are already scaled by data_manager
    flow = float(flow_raw) if flow_raw is not None else 0.0
    temp_vl = float(temp_vl_raw) if temp_vl_raw is not None else 0.0
    temp_rl = float(temp_rl_raw) if temp_rl_raw is not None else 0.0

    # Calculate temperature difference
    delta_t = temp_vl - temp_rl

    # Calculate thermal heat output: flow * |delta_t| * 70
    # The factor 70 converts from L/min × °C to Watts (water density × specific heat)
    thermal_heat_output = flow * abs(delta_t) * 70

    _LOGGER.debug(
        f"Thermal heat calculation: flow={flow} L/min, "
        f"delta_t={delta_t} K, output={thermal_heat_output} W"
    )

    return round(thermal_heat_output, 2)


def calculate_cop(
    data: dict[str, Any], external_power_sensor: str | None = None
) -> float | None:
    """Calculate Coefficient of Performance (CoP).

    Args:
        data: Dictionary containing register data
        external_power_sensor: Optional external sensor entity ID for power measurement

    Returns:
        CoP value rounded to 2 decimal places, or None if calculation not possible
    """
    # Calculate thermal heat output
    heat_power = calculate_thermal_heat_output(data)

    # Get electrical power
    electric_power = None

    if external_power_sensor:
        # External sensor case - this should be handled by the calling code
        # as it requires HA state access
        pass
    else:
        # Use internal register (input_51) - value is in kW
        power_data = data.get(REGISTER_HEAT_PUMP_POWER, {})
        electric_power_kw = power_data.get("value") if power_data else 0
        electric_power = (
            float(electric_power_kw) * 1000 if electric_power_kw is not None else None
        )  # Convert to W

    # Check if we can calculate CoP
    if electric_power is not None and electric_power >= 150 and heat_power > 0:
        # Minimum power threshold of 150 W ensures pump is actively running
        cop = heat_power / electric_power
        return round(cop, 2)
    else:
        _LOGGER.debug(
            f"Cannot calculate CoP: heat_power={heat_power} W, "
            f"electric_power={electric_power} W"
        )
        return None


def calculate_delta_t(data: dict[str, Any]) -> float:
    """Calculate temperature difference (Delta-T) between flow and return.

    Args:
        data: Dictionary containing register data

    Returns:
        Temperature difference in Kelvin/Celsius, rounded to 2 decimal places
    """
    # Leaving water temperature in °C (input_40)
    temp_vl_data = data.get(REGISTER_LEAVING_WATER_TEMP, {})
    temp_vl_raw = temp_vl_data.get("value") if temp_vl_data else 0

    # Return water temperature in °C (input_42)
    temp_rl_data = data.get(REGISTER_RETURN_WATER_TEMP, {})
    temp_rl_raw = temp_rl_data.get("value") if temp_rl_data else 0

    # Values are already scaled by data_manager
    temp_vl = float(temp_vl_raw) if temp_vl_raw is not None else 0.0
    temp_rl = float(temp_rl_raw) if temp_rl_raw is not None else 0.0

    # Calculate delta-T
    delta_t = temp_vl - temp_rl

    _LOGGER.debug(f"Delta-T calculation: {temp_vl}°C - {temp_rl}°C = {delta_t}K")

    return round(delta_t, 2)
