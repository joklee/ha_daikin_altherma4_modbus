"""Pytest configuration for ha_daikin_altherma4_modbus tests.

Marker definitions live in ``pytest.ini``; this file keeps the
session-level sys.path setup and auto-tags collected tests with the
marker matching their directory.

The test environment relies on the real installed Home Assistant
distribution together with ``pytest-homeassistant-custom-component``
(see ``requirements-test.txt``).  The former global ``homeassistant``
stub installation is intentionally NOT performed here so that tests
exercise the real Home Assistant APIs.  Any test that needs module-level
fakes must install them test-locally (e.g. via
``monkeypatch.setitem(sys.modules, ...)``) so they are reverted
automatically after the test.
"""

import sys
from pathlib import Path

import pytest

# Add project root to Python path so ``custom_components`` is importable.
PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Home Assistant's integration loader
# (homeassistant.loader._get_custom_components) discovers custom
# integrations by importing the ``custom_components`` package and scanning
# every directory listed in ``custom_components.__path__``.
#
# When the integration is installed as an editable (PEP 660) distribution
# -- e.g. via ``pip install -e .`` -- the meta-path finder exposes a
# synthetic ``__editable__...finder.__path_hook__`` entry that is not a
# real filesystem directory, and HA fails with ``FileNotFoundError`` while
# iterating it.  Normalize ``__path__`` to the repository checkout so that
# discovery always operates on the real files, independent of the local
# pip install state.
import custom_components

custom_components.__path__ = [str(PROJECT_ROOT / "custom_components")]

# Every collected test file lives below one of these sub-directories of
# ``tests/``. Tagging each test with the matching marker lets the suite be
# run by category as well as by path, e.g.::
#
#     pytest tests/unit          # by path
#     pytest -m unit             # by marker
#     pytest -m integration
#     pytest -m modbus
#     pytest -m slow
TESTS_ROOT = Path(__file__).resolve().parent

# Map the first path component under ``tests/`` to the marker(s) that are
# auto-applied to every collected item in that directory. Tests below
# ``tests/modbus`` are mock-based unit tests and therefore receive the
# ``unit`` marker in addition to the ``modbus`` marker, so the marker-based
# CI jobs (``-m unit``, ``-m integration``, ``-m slow``) cover the complete
# test suite.
_DIRECTORY_MARKERS = {
    "unit": (pytest.mark.unit,),
    "integration": (pytest.mark.integration,),
    "modbus": (pytest.mark.modbus, pytest.mark.unit),
}


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Auto-tag tests with the marker matching their directory.

    The repository organises tests into ``tests/unit``, ``tests/integration``
    and ``tests/modbus``. This hook assigns the corresponding marker to each
    collected item so that ``pytest -m unit``, ``-m integration`` and
    ``-m modbus`` select exactly the relevant tests in addition to selecting
    them by path.
    """
    for item in items:
        try:
            relative = item.path.resolve().relative_to(TESTS_ROOT)
        except ValueError:
            # The item lives outside of ``tests/`` — leave it unmarked.
            continue
        top = relative.parts[0] if relative.parts else ""
        for marker in _DIRECTORY_MARKERS.get(top, ()):
            item.add_marker(marker)
