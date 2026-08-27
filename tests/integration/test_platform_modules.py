"""Contract tests: HA-resolvable top-level platform modules must exist.

Home Assistant sets up entity platforms by importing
``custom_components.<domain>.<platform>`` (e.g. ``...sensor``) and calling its
``async_setup_entry`` coroutine. The implementation modules live below
``entities/``, so thin re-export modules are required at the package root.
A missing shim breaks boot with "No module named ...sensor" /
"Platform ... not found" errors; this regression is guarded here.
"""

import importlib
import inspect

import pytest

# Must match the platform list forwarded in ``__init__.py``.
FORWARDED_PLATFORMS = [
    "sensor",
    "binary_sensor",
    "number",
    "select",
    "climate",
    "switch",
]


@pytest.mark.parametrize("platform", FORWARDED_PLATFORMS)
def test_platform_module_exposes_async_setup_entry(platform):
    """Every forwarded platform resolves to a module with a setup hook."""
    module = importlib.import_module(
        f"custom_components.ha_daikin_altherma4_modbus.{platform}"
    )

    setup = getattr(module, "async_setup_entry", None)
    assert callable(setup), f"platform {platform} has no async_setup_entry"
    assert inspect.iscoroutinefunction(setup), (
        f"platform {platform} async_setup_entry is not a coroutine function"
    )
