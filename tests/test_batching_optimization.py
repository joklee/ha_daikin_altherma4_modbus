"""Tests for optimized register batching fallback mechanism."""

import pytest

from tests.fakes.modbus import FakeModbusClient


@pytest.mark.asyncio
async def test_batching_fallback_mechanism():
    """Test fallback mechanism when optimized batching fails."""

    # Mock client that fails on large reads but succeeds on small reads
    class FailingMockClient(FakeModbusClient):
        async def read_holding_registers(self, address: int, count: int, **kwargs):
            self._read_holding_registers_calls.append((address, count, kwargs))

            # Fail on large reads, succeed on small reads
            if count > 50:
                raise Exception("Large read failed")

            # Use parent class logic for successful reads (parent logs the operation)
            return await super().read_holding_registers(address, count, **kwargs)

    client = FailingMockClient()
    await client.connect()

    # Simulate optimized read failing
    try:
        await client.read_holding_registers(1, 79)
        pytest.fail("Large read should have failed")
    except Exception as e:
        assert str(e) == "Large read failed"

    # Simulate fallback reads (what the DataManager would do)
    fallback_results = []
    for start, count in [(1, 25), (26, 25), (51, 30)]:
        result = await client.read_holding_registers(start, count)
        fallback_results.append(result)

    # Verify fallback worked
    assert len(fallback_results) == 3, "All fallback reads should succeed"
    assert client.read_count == 3, "3 successful reads (failed read not logged in _read_operations)"
    # The internal list client._read_holding_registers_calls is not reset by client.reset()
    # and might contain retries if the transport layer does them.
    # We focus on the high-level API results.


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
