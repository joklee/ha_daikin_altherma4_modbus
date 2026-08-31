"""Helpers for loading project modules in tests.

No mocks live here. Module/import mocking is centralized in
``tests.fakes`` (Modbus fakes); these helpers only deal with filesystem paths
and importing the real ``custom_components`` modules.
"""

import importlib.util
import sys
from pathlib import Path

# tests/helpers/modules.py -> repo root
REPO_ROOT = Path(__file__).resolve().parents[2]
CUSTOM_COMPONENT_ROOT = REPO_ROOT / "custom_components"
COMPONENT_DIR = CUSTOM_COMPONENT_ROOT / "ha_daikin_altherma4_modbus"


def setup_project_paths() -> Path:
    """Add project paths to sys.path for testing.

    Returns the project root so callers can derive further paths.
    """
    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))
    if str(CUSTOM_COMPONENT_ROOT) not in sys.path:
        sys.path.insert(0, str(CUSTOM_COMPONENT_ROOT))
    return REPO_ROOT


def _load_module_by_file(module_name: str, file_path: Path):
    """Load a module directly from a file path and register it in sys.modules."""
    spec = importlib.util.spec_from_file_location(module_name, str(file_path))
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot create spec for {module_name} from {file_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def load_register_constants_module(project_root) -> object:
    """Load the register_constants module.

    register_constants.py resolves the module registry at import time via
    relative imports (``from .register_types import ...``). It is loaded with
    the real module name so those imports resolve against the real tree,
    without any Home Assistant stubs.

    Args:
        project_root: Project root path (used for custom_components lookup).

    Returns:
        The loaded ``core.register_constants`` module.
    """
    # First load register_types so register_constants' relative import works
    _load_module_by_file(
        "ha_daikin_altherma4_modbus.register_types",
        COMPONENT_DIR / "core" / "register_types.py",
    )

    # Now load register_constants which imports from .register_types
    return _load_module_by_file(
        "ha_daikin_altherma4_modbus.register_constants",
        COMPONENT_DIR / "core" / "register_constants.py",
    )
