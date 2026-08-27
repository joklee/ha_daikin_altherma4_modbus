"""Pure helpers for loading project modules in tests.

No mocks live here. Module/import mocking is centralized in
``tests.fixtures.homeassistant`` (Home Assistant stubs) and
``tests.fakes`` (Modbus fakes); these helpers only deal with filesystem paths
and importing modules from the real ``custom_components`` tree.
"""

import importlib.util
import os
import sys
from pathlib import Path

# tests/helpers/modules.py -> repo root
REPO_ROOT = Path(__file__).resolve().parents[2]
CUSTOM_COMPONENT_ROOT = REPO_ROOT / "custom_components"
COMPONENT_DIR = CUSTOM_COMPONENT_ROOT / "ha_daikin_altherma4_modbus"


def project_root() -> Path:
    """Return the repository root as an absolute :class:`Path`."""
    return REPO_ROOT


def custom_component_root() -> Path:
    """Return the custom component package directory."""
    return COMPONENT_DIR


def setup_project_paths() -> Path:
    """Add project paths to sys.path for testing.

    Returns the project root so callers can derive further paths.
    """
    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))
    if str(CUSTOM_COMPONENT_ROOT) not in sys.path:
        sys.path.insert(0, str(CUSTOM_COMPONENT_ROOT))
    return REPO_ROOT


def _ensure_import_paths() -> None:
    """Idempotently ensure project roots are importable."""
    for path in (str(REPO_ROOT), str(CUSTOM_COMPONENT_ROOT)):
        if path not in sys.path:
            sys.path.insert(0, path)


def _load_module_by_file(module_name: str, file_path: Path):
    """Load a module directly from a file path and register it in sys.modules."""
    spec = importlib.util.spec_from_file_location(module_name, str(file_path))
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot create spec for {module_name} from {file_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def load_module_by_path(module_name: str, *relative_parts: str):
    """Load a component module from the custom component tree.

    Args:
        module_name: The full dotted module name used for sys.modules.
        relative_parts: Path parts relative to the component directory, e.g.
            ``("core", "const")``.

    Returns:
        The loaded module.
    """
    _ensure_import_paths()
    file_path = COMPONENT_DIR.joinpath(*relative_parts).with_suffix(".py")
    return _load_module_by_file(module_name, file_path)


def load_const_module(project_root) -> object:
    """Load the const module for testing.

    Args:
        project_root: Project root path (used for custom_components lookup).

    Returns:
        The loaded ``core.const`` module.
    """
    return load_module_by_path("ha_daikin_altherma4_modbus.const", "core", "const")


def load_register_constants_module(project_root) -> object:
    """Load the register_constants module for testing.

    Args:
        project_root: Project root path (used for custom_components lookup).

    Returns:
        The loaded ``core.register_constants`` module.
    """
    _ensure_import_paths()

    original_cwd = os.getcwd()
    try:
        os.chdir(str(CUSTOM_COMPONENT_ROOT))

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
    finally:
        os.chdir(original_cwd)
