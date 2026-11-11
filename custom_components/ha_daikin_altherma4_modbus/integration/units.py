"""Temperature unit-system guard for the Daikin Altherma 4 integration.

The Modbus interface of the heat pump and every value this integration
writes are defined in Celsius. Home Assistant would convert absolute
temperatures to Fahrenheit for display, but the weather-dependent offset
registers are temperature *differences* and the service layer writes raw
register values, so a Fahrenheit unit system would produce wrong values.

Only an explicit Fahrenheit unit system blocks the integration. A missing or
mocked unit configuration is treated as Celsius, so isolated unit tests do not
need to build a full Home Assistant config.
"""

from homeassistant.const import UnitOfTemperature

# Tolerate minimal Home Assistant stubs used by isolated unit tests.
_FAHRENHEIT = getattr(UnitOfTemperature, "FAHRENHEIT", "°F")


def is_fahrenheit(hass) -> bool:
    """Return True only when Home Assistant is explicitly set to Fahrenheit."""
    units = getattr(getattr(hass, "config", None), "units", None)
    return getattr(units, "temperature_unit", None) == _FAHRENHEIT
