"""Pytest configuration for ha_daikin_altherma4_modbus tests."""

import sys
import types
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Setup homeassistant stubs BEFORE any imports
if "homeassistant" not in sys.modules:
    homeassistant = types.ModuleType("homeassistant")
    homeassistant.__path__ = []
    sys.modules["homeassistant"] = homeassistant

    const_module = types.ModuleType("homeassistant.const")
    const_module.EntityCategory = types.SimpleNamespace(DIAGNOSTIC="diagnostic")
    sys.modules["homeassistant.const"] = const_module

    core_module = types.ModuleType("homeassistant.core")
    core_module.Event = object
    core_module.HomeAssistant = object
    sys.modules["homeassistant.core"] = core_module

    helpers_module = types.ModuleType("homeassistant.helpers")
    helpers_module.__path__ = []
    sys.modules["homeassistant.helpers"] = helpers_module

    update_coordinator_module = types.ModuleType(
        "homeassistant.helpers.update_coordinator"
    )
    update_coordinator_module.DataUpdateCoordinator = object
    update_coordinator_module.CoordinatorEntity = object
    update_coordinator_module.UpdateFailed = Exception
    sys.modules["homeassistant.helpers.update_coordinator"] = update_coordinator_module

    helpers_typing_module = types.ModuleType("homeassistant.helpers.typing")
    helpers_typing_module.ConfigType = dict
    sys.modules["homeassistant.helpers.typing"] = helpers_typing_module
