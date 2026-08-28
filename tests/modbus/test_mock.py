"""Tests for the MockModbusTcpClient demo-mode implementation.

These tests document the actual contract of the mock client:

- Every ``read_*`` call regenerates the demo data set, so values written
  via ``write_*`` are only visible until the next read.
- ``MockModbusResponse`` uses absolute addressing: the value at response
  index ``address + i`` is taken from ``data[address + i]``, i.e. the
  data argument must be a full register array, not a slice.
- Response arrays have size ``max(address + count, len(data)) + 1`` with
  index 0 reserved as a dummy slot (registers default to 32766).
- The port argument is stored as-is without type conversion.
"""

import time

import pytest

from custom_components.ha_daikin_altherma4_modbus.modbus.mock_client import (
    MockModbusResponse,
    MockModbusTcpClient,
)


class TestInitialization:
    """Test client initialization."""

    def test_initialization(self):
        """Test client stores host/port and starts disconnected."""
        client = MockModbusTcpClient("192.168.1.100", 502)
        assert client.host == "192.168.1.100"
        assert client.port == 502
        assert client.connected is False

    def test_initialization_default_port(self):
        """Test default port is 502."""
        client = MockModbusTcpClient("localhost")
        assert client.host == "localhost"
        assert client.port == 502
        assert client.connected is False

    def test_initialization_port_stored_as_is(self):
        """Test that the port is stored without type conversion."""
        client = MockModbusTcpClient("localhost", "502")
        # The mock does not convert the port; document actual behavior.
        assert client.port == "502"

    def test_demo_data_generated_on_init(self):
        """Test demo data is generated during initialization."""
        client = MockModbusTcpClient("localhost")
        demo = client._demo_data
        assert set(demo) == {
            "input_registers",
            "holding_registers",
            "discrete_inputs",
            "coils",
        }
        assert len(demo["input_registers"]) > 0
        assert len(demo["holding_registers"]) > 0


class TestConnection:
    """Test connect/disconnect lifecycle."""

    async def test_connect_sets_connected(self):
        """Test successful connection."""
        client = MockModbusTcpClient("localhost")
        await client.connect()
        assert client.connected is True

    async def test_connect_includes_simulated_delay(self):
        """Test connection sleeps briefly to simulate latency."""
        client = MockModbusTcpClient("localhost")
        start = time.perf_counter()
        await client.connect()
        assert time.perf_counter() - start >= 0.005

    async def test_disconnect_clears_connected(self):
        """Test disconnection."""
        client = MockModbusTcpClient("localhost")
        await client.connect()
        await client.disconnect()
        assert client.connected is False

    async def test_disconnect_without_connect_is_safe(self):
        """Test disconnecting a never-connected client does not raise."""
        client = MockModbusTcpClient("localhost")
        await client.disconnect()
        assert client.connected is False

    async def test_multiple_connect_disconnect_cycles(self):
        """Test repeated connect/disconnect cycles."""
        client = MockModbusTcpClient("localhost")
        for _ in range(3):
            await client.connect()
            assert client.connected is True
            await client.disconnect()
            assert client.connected is False

    async def test_reads_work_without_connect(self):
        """Test reads do not require an active connection."""
        client = MockModbusTcpClient("localhost")
        response = await client.read_input_registers(40, 1)
        assert isinstance(response, MockModbusResponse)

    async def test_writes_work_without_connect(self):
        """Test writes do not require an active connection."""
        client = MockModbusTcpClient("localhost")
        response = await client.write_holding_register(1, 123)
        assert isinstance(response, MockModbusResponse)


class TestReads:
    """Test read operations for all register types."""

    async def test_read_input_registers_single(self):
        """Test reading one input register returns a registers response."""
        client = MockModbusTcpClient("localhost")
        response = await client.read_input_registers(40, 1)
        assert isinstance(response, MockModbusResponse)
        assert response.is_bits is False
        expected_len = max(41, len(client._demo_data["input_registers"])) + 1
        assert len(response.registers) == expected_len
        assert isinstance(response.registers[40], int)

    async def test_read_input_registers_multiple(self):
        """Test reading consecutive input registers."""
        client = MockModbusTcpClient("localhost")
        response = await client.read_input_registers(40, 5)
        for address in range(40, 45):
            assert isinstance(response.registers[address], int)

    async def test_read_holding_registers_single(self):
        """Test reading one holding register."""
        client = MockModbusTcpClient("localhost")
        response = await client.read_holding_registers(1, 1)
        assert isinstance(response, MockModbusResponse)
        assert response.is_bits is False
        expected_len = max(2, len(client._demo_data["holding_registers"])) + 1
        assert len(response.registers) == expected_len
        assert isinstance(response.registers[1], int)

    async def test_read_discrete_inputs_returns_bits(self):
        """Test discrete input reads produce a bit-array response."""
        client = MockModbusTcpClient("localhost")
        response = await client.read_discrete_inputs(1, 5)
        assert response.is_bits is True
        expected_len = max(6, len(client._demo_data["discrete_inputs"])) + 1
        assert len(response.bits) == expected_len
        for address in range(1, 6):
            assert isinstance(response.bits[address], bool)

    async def test_read_coils_returns_bits_with_known_values(self):
        """Test coil reads: generator hardcodes coils 1/2 on, 3 off."""
        client = MockModbusTcpClient("localhost")
        response = await client.read_coils(1, 3)
        assert response.is_bits is True
        assert response.bits[1] is True
        assert response.bits[2] is True
        assert response.bits[3] is False

    async def test_response_dummy_index_zero_for_registers(self):
        """Test index 0 stays at the dummy value when address >= 1."""
        client = MockModbusTcpClient("localhost")
        response = await client.read_input_registers(10, 3)
        assert response.registers[0] == 32766

    async def test_response_dummy_index_zero_for_bits(self):
        """Test index 0 of bit arrays defaults to False when address >= 1."""
        client = MockModbusTcpClient("localhost")
        response = await client.read_coils(1, 3)
        assert response.bits[0] is False

    async def test_read_addresses_across_register_map(self):
        """Test reads at several addresses succeed and stay in uint16 range."""
        client = MockModbusTcpClient("localhost")
        for address in (1, 21, 40, 63, 80):
            response = await client.read_input_registers(address, 1)
            value = response.registers[address]
            assert 0 <= value <= 65535

    async def test_read_zero_count(self):
        """Test zero-count read still returns a well-formed array."""
        client = MockModbusTcpClient("localhost")
        response = await client.read_input_registers(40, 0)
        expected_len = max(40, len(client._demo_data["input_registers"])) + 1
        assert len(response.registers) == expected_len

    async def test_repeated_reads_return_fresh_responses(self):
        """Test each read yields a new response object.

        Note: some registers (e.g. scaled temperatures) are generated from
        fixed min/max ranges, so identical values across reads are valid;
        only object freshness is asserted here.
        """
        client = MockModbusTcpClient("localhost")
        first = await client.read_input_registers(40, 1)
        second = await client.read_input_registers(40, 1)
        assert first is not second


class TestWrites:
    """Test write operations.

    The mock regenerates all demo data on every read, so written values are
    verified against internal state immediately after the write instead of
    through a subsequent read.
    """

    async def test_write_holding_register_updates_state(self):
        """Test holding-register write lands in the demo data."""
        client = MockModbusTcpClient("localhost")
        response = await client.write_holding_register(5, 777)
        assert isinstance(response, MockModbusResponse)
        assert client._demo_data["holding_registers"][5] == 777

    async def test_write_coil_updates_state(self):
        """Test coil write lands in the demo data."""
        client = MockModbusTcpClient("localhost")
        await client.write_coil_register(3, True)
        assert client._demo_data["coils"][3] is True

    async def test_write_success_response_has_no_error(self):
        """Test writes return an empty success response."""
        client = MockModbusTcpClient("localhost")
        response = await client.write_holding_register(1, 42)
        assert response.is_error() is False

    async def test_read_discards_previous_writes(self):
        """Test a read after a write regenerates data, dropping the write.

        Coil 3 is deterministically generated as False, which makes the
        regeneration observable.
        """
        client = MockModbusTcpClient("localhost")
        await client.write_coil_register(3, True)
        assert client._demo_data["coils"][3] is True
        await client.read_coils(1, 3)
        assert client._demo_data["coils"][3] is False

    async def test_write_out_of_range_address_is_ignored(self):
        """Test writes beyond the array bounds do not raise or corrupt."""
        client = MockModbusTcpClient("localhost")
        length_before = len(client._demo_data["holding_registers"])
        response = await client.write_holding_register(length_before + 500, 99)
        assert isinstance(response, MockModbusResponse)
        assert len(client._demo_data["holding_registers"]) == length_before

    async def test_write_negative_address_is_ignored(self):
        """Test negative addresses are rejected by the bounds check."""
        client = MockModbusTcpClient("localhost")
        response = await client.write_holding_register(-1, 99)
        assert isinstance(response, MockModbusResponse)
        assert client._demo_data["holding_registers"][-1] != 99

    async def test_multiple_holding_writes_before_any_read(self):
        """Test several writes accumulate while no read intervenes."""
        client = MockModbusTcpClient("localhost")
        for address in (1, 2, 3, 4, 5):
            await client.write_holding_register(address, address * 10)
        for address in (1, 2, 3, 4, 5):
            assert client._demo_data["holding_registers"][address] == address * 10

    async def test_multiple_coil_writes_before_any_read(self):
        """Test several coil writes accumulate while no read intervenes."""
        client = MockModbusTcpClient("localhost")
        for address in (1, 2, 3):
            await client.write_coil_register(address, address % 2 == 0)
        assert client._demo_data["coils"][1] is False
        assert client._demo_data["coils"][2] is True
        assert client._demo_data["coils"][3] is False


class TestDemoData:
    """Test structure of the generated demo data."""

    def test_discrete_inputs_layout(self):
        """Test discrete inputs span indices 0-26 with False filler at 0."""
        demo = MockModbusTcpClient.generate_demo_register_data()
        assert len(demo["discrete_inputs"]) == 27
        assert demo["discrete_inputs"][0] is False

    def test_coils_layout(self):
        """Test coils span indices 0-3 with deterministic values."""
        demo = MockModbusTcpClient.generate_demo_register_data()
        assert len(demo["coils"]) == 4
        assert demo["coils"][0] is False
        assert demo["coils"][1] is True
        assert demo["coils"][2] is True
        assert demo["coils"][3] is False

    def test_register_arrays_are_uint16(self):
        """Test generated register values fit in unsigned 16-bit."""
        demo = MockModbusTcpClient.generate_demo_register_data()
        for value in demo["input_registers"]:
            assert 0 <= value <= 65535
        for value in demo["holding_registers"]:
            assert 0 <= value <= 65535

    def test_static_generation_without_instance(self):
        """Test the generator works as a pure static method."""
        first = MockModbusTcpClient.generate_demo_register_data()
        second = MockModbusTcpClient.generate_demo_register_data()
        assert len(first["input_registers"]) == len(second["input_registers"])
        assert len(first["holding_registers"]) == len(second["holding_registers"])


def _make_register_response(data, address, count):
    """Build a registers-style MockModbusResponse."""
    return MockModbusResponse(data, address, count, is_bits=False)


def _make_bit_response(data, address, count):
    """Build a bits-style MockModbusResponse."""
    return MockModbusResponse(data, address, count, is_bits=True)


class TestMockModbusResponseRegisters:
    """Direct unit tests for MockModbusResponse (register mode)."""

    def test_absolute_addressing_into_full_array(self):
        """Test values map as registers[address+i] = data[address+i]."""
        data = list(range(20))  # index i holds value i
        response = _make_register_response(data, 10, 3)
        assert response.is_bits is False
        assert response.registers[10] == 10
        assert response.registers[11] == 11
        assert response.registers[12] == 12

    def test_size_is_max_of_window_and_data_plus_one(self):
        """Test array sizing rule max(address+count, len(data)) + 1."""
        data = list(range(20))
        response = _make_register_response(data, 10, 3)
        assert len(response.registers) == max(13, 20) + 1

    def test_size_grows_for_large_window(self):
        """Test window larger than data extends the array."""
        data = [7, 8]
        response = _make_register_response(data, 30, 2)
        assert len(response.registers) == 33

    def test_out_of_window_slots_keep_default(self):
        """Test slots outside the copied window remain 32766."""
        data = list(range(20))
        response = _make_register_response(data, 10, 3)
        assert response.registers[9] == 32766
        assert response.registers[13] == 32766

    def test_data_beyond_window_is_replaced_with_default(self):
        """Test slots outside the copied window reset to 32766.

        The constructor pre-fills the whole array with the default value and
        copies only the requested window, so original data at indices outside
        ``[address, address + count)`` does not survive.
        """
        data = list(range(20))
        response = _make_register_response(data, 0, 2)
        assert response.registers[0] == 0
        assert response.registers[1] == 1
        assert response.registers[19] == 32766

    def test_address_past_end_of_data_yields_defaults(self):
        """Test requesting beyond len(data) fills with 32766."""
        response = _make_register_response([100, 200], 30, 2)
        assert response.registers[30] == 32766
        assert response.registers[31] == 32766

    def test_zero_count_copies_nothing(self):
        """Test count=0 leaves every slot at its initial value."""
        data = [100, 200]
        response = _make_register_response(data, 0, 0)
        # Size is still max(0 + 0, len(data)) + 1 = 3; nothing gets copied.
        assert response.registers == [32766, 32766, 32766]

    def test_no_error_by_default(self):
        """Test responses start in non-error state."""
        response = _make_register_response([1], 0, 1)
        assert response.is_error() is False

    def test_error_state_can_be_flagged(self):
        """Test toggling the internal error flag."""
        response = _make_register_response([1], 0, 1)
        response._error = True
        assert response.is_error() is True


class TestMockModbusResponseBits:
    """Direct unit tests for MockModbusResponse (bit mode)."""

    def test_absolute_addressing_bits(self):
        """Test bit mapping follows the same absolute-address rule."""
        data = [False] + [True] * 26  # index i mirrors address i
        response = _make_bit_response(data, 1, 3)
        assert response.is_bits is True
        assert response.bits[1] is True
        assert response.bits[2] is True
        assert response.bits[3] is True

    def test_size_bits(self):
        """Test bit-array sizing rule."""
        data = [False] * 27
        response = _make_bit_response(data, 1, 3)
        assert len(response.bits) == max(4, 27) + 1

    def test_out_of_window_bits_default_false(self):
        """Test untouched bit slots default to False."""
        data = [False] + [True] * 5
        response = _make_bit_response(data, 1, 2)
        assert response.bits[3] is False
        assert response.bits[4] is False

    def test_address_past_end_of_data_bits(self):
        """Test requesting beyond len(data) fills with False."""
        response = _make_bit_response([True, True], 30, 2)
        assert response.bits[30] is False
        assert response.bits[31] is False

    def test_zero_count_bits(self):
        """Test count=0 leaves all bit slots False."""
        response = _make_bit_response([True, True], 0, 0)
        # Size is max(0 + 0, len(data)) + 1 = 3; nothing gets copied.
        assert response.bits == [False, False, False]

    def test_no_error_by_default_bits(self):
        """Test bit responses start in non-error state."""
        response = _make_bit_response([True], 0, 1)
        assert response.is_error() is False


class TestMockModbusResponseContract:
    """Guard against accidental interface drift."""

    def test_only_is_error_exists_not_iserror(self):
        """MockModbusResponse exposes is_error(); isError() belongs to the
        FakeModbusResponse test double, not this class."""
        response = _make_register_response([1], 0, 1)
        assert callable(response.is_error)
        assert not hasattr(response, "isError")

    def test_no_len_protocol(self):
        """len() is intentionally unsupported on responses."""
        response = _make_register_response([1], 0, 1)
        with pytest.raises(TypeError):
            len(response)
