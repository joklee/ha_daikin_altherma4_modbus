"""Pytest fixtures for register data."""

import pytest

from tests.fakes.responses import generate_demo_register_data


@pytest.fixture
def demo_register_data():
    """Return demo register data for testing."""
    return generate_demo_register_data()


@pytest.fixture
def input_registers(demo_register_data):
    """Return demo input registers."""
    return demo_register_data["input_registers"]


@pytest.fixture
def holding_registers(demo_register_data):
    """Return demo holding registers."""
    return demo_register_data["holding_registers"]


@pytest.fixture
def discrete_inputs(demo_register_data):
    """Return demo discrete inputs."""
    return demo_register_data["discrete_inputs"]


@pytest.fixture
def coils(demo_register_data):
    """Return demo coils."""
    return demo_register_data["coils"]
