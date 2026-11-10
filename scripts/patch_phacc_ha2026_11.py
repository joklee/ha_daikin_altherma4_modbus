#!/usr/bin/env python3
"""Apply the temporary harness patches needed to run against HA >= 2026.11.

``pytest-homeassistant-custom-component`` 0.13.375 pins and ships Home
Assistant 2026.10.4. To test this integration's 2026.11-only code paths
against a real HA 2026.11 runtime, the test environment overrides
``homeassistant`` with ``>= 2026.11`` (see ``.github/workflows/ci.yml``,
"Override Home Assistant for the pytest jobs"). That override exposes two
harness incompatibilities, which this script patches **idempotently** in the
installed ``pytest_homeassistant_custom_component`` package:

1. ``plugins.py`` imports ``respx`` (and therefore ``httpx``) before
   ``homeassistant``, but HA 2026.11 aliases ``httpx`` to ``httpx2`` inside
   ``homeassistant/__init__.py`` and refuses any earlier ``httpx`` import.
   Home Assistant core disables the respx *plugin* the same way (see their
   ``pyproject.toml``: ``addopts = "-p no:respx"``) and our ``pytest.ini``
   follows suit. The module-level ``import respx`` inside the harness itself
   is converted into a lazy import in the only place it is used (the global
   per-test cleanup), which runs after ``homeassistant`` was imported.

2. ``common.py`` imports ``_clear_logger_overwrites`` from
   ``homeassistant.components.logger``, but HA 2026.11 moved that helper to
   ``homeassistant.components.logger.helpers``.

REMOVE this script, the CI patch step, the ``-p no:respx`` line in
``pytest.ini`` and the HA override step as soon as
``pytest-homeassistant-custom-component`` ships a release bundled with Home
Assistant 2026.11.
"""

from __future__ import annotations

import sys
from pathlib import Path


def _patch(path: Path, old: str, new: str, marker: str, *, unique_target=True) -> bool:
    """Apply one idempotent patch; return True when changes were made.

    When ``unique_target`` is set (default), the new text only shortcuts the
    patch when it appears in the file. For replacements whose new text also
    exists in the *pristine* file, pass ``unique_target=False`` and guard
    the call site with an explicit already-applied check.

    Fails loudly when the pattern is neither present nor already patched, so
    drift in ``pytest-homeassistant-custom-component`` cannot silently pass.
    """
    text = path.read_text()
    if unique_target and new in text:
        print(f"  [skip] {marker} (already applied)")
        return False
    if old not in text:
        print(
            f"  [FAIL] {marker}: expected pattern not found in {path}.\n"
            f"         pytest-homeassistant-custom-component changed — update\n"
            f"         this script or remove it once it bundles HA 2026.11."
        )
        raise SystemExit(1)
    path.write_text(text.replace(old, new, 1))
    print(f"  [ok]   {marker}")
    return True


def main() -> None:
    try:
        import pytest_homeassistant_custom_component as phacc
    except ImportError:
        print(
            "pytest-homeassistant-custom-component is not installed; nothing to patch"
        )
        return

    pkg = Path(phacc.__file__).parent
    print(f"Patching pytest-homeassistant-custom-component at {pkg}")

    # 1. plugins.py: remove the module-level respx import (loads httpx before
    #    homeassistant and breaks the HA 2026.11 httpx2 aliasing) ...
    plugins = pkg / "plugins.py"
    if "\nimport respx\n" not in plugins.read_text():
        print("  [skip] plugins.py: drop module-level 'import respx' (already applied)")
    else:
        _patch(
            plugins,
            old="\nimport respx\nfrom syrupy.assertion import SnapshotAssertion\n",
            new="\nfrom syrupy.assertion import SnapshotAssertion\n",
            marker="plugins.py: drop module-level 'import respx'",
            unique_target=False,
        )
    # ... and make the only usage a lazy import inside the global cleanup.
    _patch(
        plugins,
        old="""    try:
        # Verify respx.mock has been cleaned up
        assert not respx.mock.routes, (
            "respx.mock routes not cleaned up, maybe the test"
            " needs to be decorated with @respx.mock"
        )
    finally:
        # Clear mock routes not break subsequent tests
        respx.mock.clear()
""",
        new="""    try:
        # Lazy import: HA 2026.11 aliases httpx to httpx2 in
        # homeassistant/__init__.py, which must run before any httpx import;
        # by the time this cleanup runs, homeassistant was imported.
        import respx

        # Verify respx.mock has been cleaned up
        assert not respx.mock.routes, (
            "respx.mock routes not cleaned up, maybe the test"
            " needs to be decorated with @respx.mock"
        )
    finally:
        # Clear mock routes not break subsequent tests
        respx.mock.clear()
""",
        marker="plugins.py: lazy respx import in global cleanup",
    )

    # 2. common.py: HA 2026.11 moved _clear_logger_overwrites to logger.helpers.
    _patch(
        pkg / "common.py",
        old="""from homeassistant.components.logger import (
    DOMAIN as LOGGER_DOMAIN,
    SERVICE_SET_LEVEL,
    _clear_logger_overwrites,
)
""",
        new="""from homeassistant.components.logger import (
    DOMAIN as LOGGER_DOMAIN,
    SERVICE_SET_LEVEL,
)
from homeassistant.components.logger.helpers import _clear_logger_overwrites
""",
        marker="common.py: _clear_logger_overwrites from logger.helpers",
    )


if __name__ == "__main__":
    sys.exit(main())
