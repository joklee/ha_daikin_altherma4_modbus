"""Tests for modbus_client.py module."""

import importlib
import sys
import types
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest


def _reset_modules(*names: str) -> None:
    for name in names:
        sys.modules.pop(name, None)


def _install_fake_package(monkeypatch) -> str:
    package_name = "custom_components.ha_daikin_altherma4_modbus"
    package_path = (
        Path(__file__).resolve().parents[1]
        / "custom_components"
        / "ha_daikin_altherma4_modbus"
    )
    package_module = types.ModuleType(package_name)
    package_module.__path__ = [str(package_path)]
    monkeypatch.setitem(sys.modules, package_name, package_module)
    return package_name


def _load_modbus_client_module(monkeypatch, mock_pymodbus=True):
    """Load modbus_client module with mocked dependencies."""
    package_name = _install_fake_package(monkeypatch)
    module_name = f"{package_name}.modbus_client"
    client_interface_name = f"{package_name}.client_interface"
    exceptions_name = f"{package_name}.exceptions"

    _reset_modules(
        module_name,
        client_interface_name,
        exceptions_name,
        "pymodbus",
        "pymodbus.exceptions",
        "pymodbus.client",
    )

    # Mock exceptions module
    exceptions_module = types.ModuleType(exceptions_name)

    class ModbusDeviceException(Exception):
        pass

    class ModbusReadException(Exception):
        pass

    class ModbusTimeoutException(Exception):
        pass

    class ModbusWriteException(Exception):
        pass

    exceptions_module.ModbusDeviceException = ModbusDeviceException
    exceptions_module.ModbusReadException = ModbusReadException
    exceptions_module.ModbusTimeoutException = ModbusTimeoutException
    exceptions_module.ModbusWriteException = ModbusWriteException
    monkeypatch.setitem(sys.modules, exceptions_name, exceptions_module)

    # Mock client_interface module
    client_interface_module = types.ModuleType(client_interface_name)

    class ModbusClientInterface:
        pass

    client_interface_module.ModbusClientInterface = ModbusClientInterface
    monkeypatch.setitem(sys.modules, client_interface_name, client_interface_module)

    if mock_pymodbus:
        # Mock pymodbus
        pymodbus_module = types.ModuleType("pymodbus")
        pymodbus_exceptions = types.ModuleType("pymodbus.exceptions")

        class ModbusIOException(Exception):
            pass

        class ModbusException(Exception):
            pass

        pymodbus_exceptions.ModbusIOException = ModbusIOException
        pymodbus_exceptions.ModbusException = ModbusException
        monkeypatch.setitem(sys.modules, "pymodbus.exceptions", pymodbus_exceptions)
        pymodbus_module.exceptions = pymodbus_exceptions  # Add as attribute

        # Mock AsyncModbusTcpClient
        mock_client_class = Mock()
        pymodbus_client = types.ModuleType("pymodbus.client")
        pymodbus_client.AsyncModbusTcpClient = mock_client_class
        monkeypatch.setitem(sys.modules, "pymodbus.client", pymodbus_client)

        monkeypatch.setitem(sys.modules, "pymodbus", pymodbus_module)

    return importlib.import_module(module_name)


@pytest.fixture
def mock_async_client():
    """Create a mock AsyncModbusTcpClient."""
    client = Mock()
    client.connected = True
    client.connect = AsyncMock()
    client.close = Mock()
    client.read_input_registers = AsyncMock()
    client.read_holding_registers = AsyncMock()
    client.read_discrete_inputs = AsyncMock()
    client.read_coils = AsyncMock()
    client.write_register = AsyncMock()
    client.write_coil = AsyncMock()
    return client


def test_one_based_modbus_response_registers(monkeypatch):
    """Test OneBasedModbusResponse registers property."""
    modbus_client = _load_modbus_client_module(monkeypatch, mock_pymodbus=False)

    # Mock response with registers
    original_response = Mock()
    original_response.registers = [100, 200, 300]

    response = modbus_client.OneBasedModbusResponse(original_response, start_address=10)

    # Registers should be 1-indexed, with values at positions 10, 11, 12
    registers = response.registers
    assert len(registers) >= 13  # Should include index 0-12
    assert registers[10] == 100
    assert registers[11] == 200
    assert registers[12] == 300
    # Unset positions should have unavailable value
    assert registers[0] == 32766


def test_one_based_modbus_response_bits(monkeypatch):
    """Test OneBasedModbusResponse bits property."""
    modbus_client = _load_modbus_client_module(monkeypatch, mock_pymodbus=False)

    # Mock response with bits
    original_response = Mock()
    original_response.bits = [True, False, True]

    response = modbus_client.OneBasedModbusResponse(
        original_response, start_address=5, is_bits=True
    )

    # Bits should be 1-indexed
    bits = response.bits
    assert len(bits) >= 8  # Should include index 0-7
    assert bits[5] is True
    assert bits[6] is False
    assert bits[7] is True
    # Unset positions should be False
    assert bits[0] is False


def test_one_based_modbus_response_is_error(monkeypatch):
    """Test OneBasedModbusResponse is_error method."""
    modbus_client = _load_modbus_client_module(monkeypatch, mock_pymodbus=False)

    # Response with error
    error_response = Mock()
    error_response.isError.return_value = True

    response = modbus_client.OneBasedModbusResponse(error_response, start_address=1)
    assert response.is_error() is True

    # Response without error
    ok_response = Mock()
    ok_response.isError.return_value = False

    response = modbus_client.OneBasedModbusResponse(ok_response, start_address=1)
    assert response.is_error() is False


def test_one_based_modbus_response_no_registers(monkeypatch):
    """Test OneBasedModbusResponse when original has no registers."""
    modbus_client = _load_modbus_client_module(monkeypatch, mock_pymodbus=False)

    original_response = Mock()
    # No registers attribute
    del original_response.registers

    response = modbus_client.OneBasedModbusResponse(original_response, start_address=1)
    assert response.registers == [32766]


def test_one_based_modbus_response_no_bits(monkeypatch):
    """Test OneBasedModbusResponse when original has no bits."""
    modbus_client = _load_modbus_client_module(monkeypatch, mock_pymodbus=False)

    original_response = Mock()
    # No bits attribute
    del original_response.bits

    response = modbus_client.OneBasedModbusResponse(
        original_response, start_address=1, is_bits=True
    )
    assert response.bits == [False]


@pytest.mark.asyncio
async def test_real_modbus_tcp_client_create(monkeypatch, mock_async_client):
    """Test RealModbusTcpClient.create factory method."""
    modbus_client = _load_modbus_client_module(monkeypatch)

    # Patch AsyncModbusTcpClient to return our mock
    with patch.object(
        modbus_client, "AsyncModbusTcpClient", return_value=mock_async_client
    ):
        client = await modbus_client.RealModbusTcpClient.create(
            "192.168.1.100", port=502, timeout=10
        )

        assert client.host == "192.168.1.100"
        assert client.port == 502
        assert client.timeout == 10
        assert client._client is not None


@pytest.mark.asyncio
async def test_real_modbus_tcp_client_connected_property(
    monkeypatch, mock_async_client
):
    """Test RealModbusTcpClient.connected property."""
    modbus_client = _load_modbus_client_module(monkeypatch)

    with patch.object(
        modbus_client, "AsyncModbusTcpClient", return_value=mock_async_client
    ):
        client = await modbus_client.RealModbusTcpClient.create(
            "192.168.1.100", port=502
        )

        assert client.connected is True

        # Test when client is None
        client._client = None
        assert client.connected is False


@pytest.mark.asyncio
async def test_real_modbus_tcp_client_connect(monkeypatch, mock_async_client):
    """Test RealModbusTcpClient.connect method."""
    modbus_client = _load_modbus_client_module(monkeypatch)

    mock_async_client.connected = False

    with patch.object(
        modbus_client, "AsyncModbusTcpClient", return_value=mock_async_client
    ):
        client = await modbus_client.RealModbusTcpClient.create(
            "192.168.1.100", port=502
        )

        await client.connect()

        mock_async_client.connect.assert_called_once()
        assert client._reconnect_needed is False


@pytest.mark.asyncio
async def test_real_modbus_tcp_client_connect_already_connected(
    monkeypatch, mock_async_client
):
    """Test RealModbusTcpClient.connect when already connected."""
    modbus_client = _load_modbus_client_module(monkeypatch)

    mock_async_client.connected = True

    with patch.object(
        modbus_client, "AsyncModbusTcpClient", return_value=mock_async_client
    ):
        client = await modbus_client.RealModbusTcpClient.create(
            "192.168.1.100", port=502
        )
        client._reconnect_needed = False

        await client.connect()

        # Should not call connect again
        mock_async_client.connect.assert_not_called()


@pytest.mark.asyncio
async def test_real_modbus_tcp_client_disconnect(monkeypatch, mock_async_client):
    """Test RealModbusTcpClient.disconnect method."""
    modbus_client = _load_modbus_client_module(monkeypatch)

    mock_async_client.connected = True

    with patch.object(
        modbus_client, "AsyncModbusTcpClient", return_value=mock_async_client
    ):
        client = await modbus_client.RealModbusTcpClient.create(
            "192.168.1.100", port=502
        )

        await client.disconnect()

        mock_async_client.close.assert_called_once()
        assert client._reconnect_needed is True


@pytest.mark.asyncio
async def test_real_modbus_tcp_client_read_input_registers(
    monkeypatch, mock_async_client
):
    """Test RealModbusTcpClient.read_input_registers method."""
    modbus_client = _load_modbus_client_module(monkeypatch)

    # Mock response
    mock_response = Mock()
    mock_response.registers = [100, 200]
    mock_response.isError.return_value = False
    mock_async_client.read_input_registers.return_value = mock_response

    with patch.object(
        modbus_client, "AsyncModbusTcpClient", return_value=mock_async_client
    ):
        client = await modbus_client.RealModbusTcpClient.create(
            "192.168.1.100", port=502
        )

        response = await client.read_input_registers(10, count=2)

        # Address should be 0-based for pymodbus (10 -> 9)
        mock_async_client.read_input_registers.assert_called_once_with(9, count=2)
        assert hasattr(response, "registers")


@pytest.mark.asyncio
async def test_real_modbus_tcp_client_read_input_registers_error(
    monkeypatch, mock_async_client
):
    """Test RealModbusTcpClient.read_input_registers with error response."""
    modbus_client = _load_modbus_client_module(monkeypatch)

    # Mock error response
    mock_response = Mock()
    mock_response.isError.return_value = True
    mock_async_client.read_input_registers.return_value = mock_response

    with patch.object(
        modbus_client, "AsyncModbusTcpClient", return_value=mock_async_client
    ):
        client = await modbus_client.RealModbusTcpClient.create(
            "192.168.1.100", port=502
        )

        # ModbusDeviceException is raised but then caught by generic Exception handler
        # and wrapped in ModbusReadException
        with pytest.raises(modbus_client.ModbusReadException):
            await client.read_input_registers(10, count=2)


@pytest.mark.asyncio
async def test_real_modbus_tcp_client_read_holding_registers(
    monkeypatch, mock_async_client
):
    """Test RealModbusTcpClient.read_holding_registers method."""
    modbus_client = _load_modbus_client_module(monkeypatch)

    mock_response = Mock()
    mock_response.registers = [50, 60]
    mock_response.isError.return_value = False
    mock_async_client.read_holding_registers.return_value = mock_response

    with patch.object(
        modbus_client, "AsyncModbusTcpClient", return_value=mock_async_client
    ):
        client = await modbus_client.RealModbusTcpClient.create(
            "192.168.1.100", port=502
        )

        response = await client.read_holding_registers(20, count=2)

        mock_async_client.read_holding_registers.assert_called_once_with(19, count=2)
        assert hasattr(response, "registers")


@pytest.mark.asyncio
async def test_real_modbus_tcp_client_read_discrete_inputs(
    monkeypatch, mock_async_client
):
    """Test RealModbusTcpClient.read_discrete_inputs method."""
    modbus_client = _load_modbus_client_module(monkeypatch)

    mock_response = Mock()
    mock_response.bits = [True, False]
    mock_response.isError.return_value = False
    mock_async_client.read_discrete_inputs.return_value = mock_response

    with patch.object(
        modbus_client, "AsyncModbusTcpClient", return_value=mock_async_client
    ):
        client = await modbus_client.RealModbusTcpClient.create(
            "192.168.1.100", port=502
        )

        response = await client.read_discrete_inputs(5, count=2)

        mock_async_client.read_discrete_inputs.assert_called_once_with(4, count=2)
        assert hasattr(response, "bits")


@pytest.mark.asyncio
async def test_real_modbus_tcp_client_read_coils(monkeypatch, mock_async_client):
    """Test RealModbusTcpClient.read_coils method."""
    modbus_client = _load_modbus_client_module(monkeypatch)

    mock_response = Mock()
    mock_response.bits = [True, True, False]
    mock_response.isError.return_value = False
    mock_async_client.read_coils.return_value = mock_response

    with patch.object(
        modbus_client, "AsyncModbusTcpClient", return_value=mock_async_client
    ):
        client = await modbus_client.RealModbusTcpClient.create(
            "192.168.1.100", port=502
        )

        response = await client.read_coils(1, count=3)

        mock_async_client.read_coils.assert_called_once_with(0, count=3)
        assert hasattr(response, "bits")


@pytest.mark.asyncio
async def test_real_modbus_tcp_client_write_holding_register(
    monkeypatch, mock_async_client
):
    """Test RealModbusTcpClient.write_holding_register method."""
    modbus_client = _load_modbus_client_module(monkeypatch)

    mock_response = Mock()
    mock_response.isError.return_value = False
    mock_async_client.write_register.return_value = mock_response

    with patch.object(
        modbus_client, "AsyncModbusTcpClient", return_value=mock_async_client
    ):
        client = await modbus_client.RealModbusTcpClient.create(
            "192.168.1.100", port=502
        )

        result = await client.write_holding_register(10, value=100)

        # Address should be 0-based (10 -> 9)
        mock_async_client.write_register.assert_called_once_with(9, 100)
        assert result is mock_response


@pytest.mark.asyncio
async def test_real_modbus_tcp_client_write_coil_register(
    monkeypatch, mock_async_client
):
    """Test RealModbusTcpClient.write_coil_register method."""
    modbus_client = _load_modbus_client_module(monkeypatch)

    mock_response = Mock()
    mock_response.isError.return_value = False
    mock_async_client.write_coil.return_value = mock_response

    with patch.object(
        modbus_client, "AsyncModbusTcpClient", return_value=mock_async_client
    ):
        client = await modbus_client.RealModbusTcpClient.create(
            "192.168.1.100", port=502
        )

        result = await client.write_coil_register(5, value=True)

        # Address should be 0-based (5 -> 4)
        mock_async_client.write_coil.assert_called_once_with(4, True)
        assert result is mock_response


@pytest.mark.asyncio
async def test_real_modbus_tcp_client_clear_cache(monkeypatch, mock_async_client):
    """Test RealModbusTcpClient.clear_cache method."""
    modbus_client = _load_modbus_client_module(monkeypatch)

    with patch.object(
        modbus_client, "AsyncModbusTcpClient", return_value=mock_async_client
    ):
        _ = await modbus_client.RealModbusTcpClient.create("192.168.1.100", port=502)

        # Clear cache
        modbus_client.RealModbusTcpClient.clear_cache()

        assert len(modbus_client._client_cache) == 0
        assert len(modbus_client._client_locks) == 0


@pytest.mark.asyncio
async def test_real_modbus_tcp_client_safe_clear_cache(monkeypatch, mock_async_client):
    """Test RealModbusTcpClient.safe_clear_cache method."""
    modbus_client = _load_modbus_client_module(monkeypatch)

    with patch.object(
        modbus_client, "AsyncModbusTcpClient", return_value=mock_async_client
    ):
        _ = await modbus_client.RealModbusTcpClient.create("192.168.1.100", port=502)

        # Safe clear cache
        await modbus_client.RealModbusTcpClient.safe_clear_cache()

        assert len(modbus_client._client_cache) == 0
        assert len(modbus_client._client_locks) == 0


@pytest.mark.asyncio
async def test_real_modbus_tcp_client_async_close_cached_client(
    monkeypatch, mock_async_client
):
    """Test RealModbusTcpClient.async_close_cached_client method."""
    modbus_client = _load_modbus_client_module(monkeypatch)

    mock_async_client.connected = True

    with patch.object(
        modbus_client, "AsyncModbusTcpClient", return_value=mock_async_client
    ):
        _ = await modbus_client.RealModbusTcpClient.create("192.168.1.100", port=502)

        # Close specific cached client
        await modbus_client.RealModbusTcpClient.async_close_cached_client(
            "192.168.1.100", port=502
        )

        mock_async_client.close.assert_called_once()
        assert "192.168.1.100:502" not in modbus_client._client_cache


@pytest.mark.asyncio
async def test_real_modbus_tcp_client_async_close_cached_client_not_connected(
    monkeypatch, mock_async_client
):
    """Test async_close_cached_client when client not connected."""
    modbus_client = _load_modbus_client_module(monkeypatch)

    mock_async_client.connected = False

    with patch.object(
        modbus_client, "AsyncModbusTcpClient", return_value=mock_async_client
    ):
        _ = await modbus_client.RealModbusTcpClient.create("192.168.1.100", port=502)

        # Close should not raise error even if not connected
        await modbus_client.RealModbusTcpClient.async_close_cached_client(
            "192.168.1.100", port=502
        )

        mock_async_client.close.assert_not_called()


@pytest.mark.asyncio
async def test_real_modbus_tcp_client_client_caching(monkeypatch, mock_async_client):
    """Test that RealModbusTcpClient reuses cached clients."""
    modbus_client = _load_modbus_client_module(monkeypatch)

    with patch.object(
        modbus_client, "AsyncModbusTcpClient", return_value=mock_async_client
    ):
        # Create first client
        client1 = await modbus_client.RealModbusTcpClient.create(
            "192.168.1.100", port=502
        )

        # Create second client with same host:port
        client2 = await modbus_client.RealModbusTcpClient.create(
            "192.168.1.100", port=502
        )

        # Should reuse the same underlying client
        assert client1._client is client2._client
        assert client1._lock is client2._lock


def test_is_modbus_error_with_isError(monkeypatch):
    """Test _is_modbus_error when response has isError method."""
    modbus_client = _load_modbus_client_module(monkeypatch, mock_pymodbus=False)

    response = Mock()
    response.isError.return_value = True

    result = modbus_client.RealModbusTcpClient._is_modbus_error(response)
    assert result is True

    response.isError.return_value = False
    result = modbus_client.RealModbusTcpClient._is_modbus_error(response)
    assert result is False


def test_is_modbus_error_with_exception_code(monkeypatch):
    """Test _is_modbus_error when response has exception_code."""
    modbus_client = _load_modbus_client_module(monkeypatch, mock_pymodbus=False)

    # Response with function_code >= 0x80 indicates error
    response = Mock()
    del response.isError  # Remove isError method
    response.function_code = 0x81
    response.exception_code = 1

    result = modbus_client.RealModbusTcpClient._is_modbus_error(response)
    assert result is True

    # Normal function code
    response.function_code = 0x01
    result = modbus_client.RealModbusTcpClient._is_modbus_error(response)
    assert result is False


def test_is_modbus_error_no_error_attributes(monkeypatch):
    """Test _is_modbus_error when response has no error attributes."""
    modbus_client = _load_modbus_client_module(monkeypatch, mock_pymodbus=False)

    response = Mock()
    del response.isError
    del response.function_code

    result = modbus_client.RealModbusTcpClient._is_modbus_error(response)
    assert result is False
