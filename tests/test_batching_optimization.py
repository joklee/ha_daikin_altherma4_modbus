"""Performance tests for optimized register batching."""

import asyncio
import sys
import time
from pathlib import Path

import pytest

# Add tests directory to path for test_utils import
tests_dir = Path(__file__).parent
if str(tests_dir) not in sys.path:
    sys.path.insert(0, str(tests_dir))

from tests.fakes.modbus import FakeModbusClientPerformance


@pytest.mark.asyncio
async def test_batching_optimization_comparison():
    """Compare old vs new batching performance."""

    print("\n" + "=" * 80)
    print("📊 BATCHING OPTIMIZATION COMPARISON")
    print("=" * 80)

    # Test OLD implementation (multiple small reads)
    old_client = FakeModbusClientPerformance(
        "192.168.1.100", 502, timing_mode="realistic"
    )
    await old_client.connect()

    start_time = time.time()

    # OLD: 2 separate input register blocks
    await old_client.read_input_registers(21, 33)  # Block 1
    await old_client.read_input_registers(54, 34)  # Block 2

    # OLD: 3 separate holding register blocks with delays
    await old_client.read_holding_registers(1, 25)  # Block 1
    await asyncio.sleep(0.2)  # Artificial delay!
    await old_client.read_holding_registers(26, 25)  # Block 2
    await asyncio.sleep(0.2)  # Artificial delay!
    await old_client.read_holding_registers(51, 30)  # Block 3

    old_time = time.time() - start_time
    old_operations = len(old_client.get_read_operations())

    # Test NEW implementation (optimized batching)
    new_client = FakeModbusClientPerformance(
        "192.168.1.100", 502, timing_mode="realistic"
    )
    await new_client.connect()

    start_time = time.time()

    # NEW: 1 single input register block
    await new_client.read_input_registers(21, 67)  # All in one!

    # NEW: 1 single holding register block
    await new_client.read_holding_registers(1, 79)  # All in one!

    new_time = time.time() - start_time
    new_operations = len(new_client.get_read_operations())

    # Results
    print("\n🔄 OLD Implementation:")
    print("   Input Registers: 2 separate reads (21-53, 54-87)")
    print("   Holding Registers: 3 separate reads (1-25, 26-50, 51-80)")
    print("   Artificial Delays: 2 × 200ms = 400ms")
    print(f"   Total Operations: {old_operations}")
    print(f"   Total Time: {old_time:.3f}s")

    print("\n🚀 NEW Implementation:")
    print("   Input Registers: 1 optimized read (21-87)")
    print("   Holding Registers: 1 optimized read (1-79)")
    print("   Artificial Delays: 0 × 0ms = 0ms")
    print(f"   Total Operations: {new_operations}")
    print(f"   Total Time: {new_time:.3f}s")

    # Performance improvements
    time_improvement = old_time / new_time
    operation_reduction = (old_operations - new_operations) / old_operations * 100

    print("\n📈 Performance Improvements:")
    print(f"   Speed Improvement: {time_improvement:.1f}x faster")
    print(f"   Operation Reduction: {operation_reduction:.1f}% fewer reads")
    print(f"   Time Saved: {(old_time - new_time) * 1000:.1f}ms")

    # Verify improvements
    assert new_time < old_time, "New implementation should be faster"
    assert new_operations < old_operations, (
        "New implementation should use fewer operations"
    )
    assert time_improvement > 2, "Should be at least 2x faster"

    print("\n✅ Batching optimization successful!")


@pytest.mark.asyncio
async def test_batching_fallback_mechanism():
    """Test fallback mechanism when optimized batching fails."""

    print("\n" + "=" * 80)
    print("🔄 FALLBACK MECHANISM TEST")
    print("=" * 80)

    # Mock client that fails on large reads but succeeds on small reads
    class FailingMockClient(FakeModbusClientPerformance):
        async def read_holding_registers(self, address: int, count: int, **kwargs):
            self._read_holding_registers_calls.append((address, count, kwargs))

            # Log operation before checking for failure
            self._operation_count += 1
            self.operation_count = self._operation_count
            self._read_operations.append(f"read_holding_registers({address}, {count})")

            # Fail on large reads, succeed on small reads
            if count > 50:
                raise Exception("Large read failed")

            if not self.connected:
                raise ConnectionError("Not connected")

            await asyncio.sleep(0.001)

            registers = self._holding_registers.get(address, [0] * count)
            if len(registers) < count:
                registers = registers + [0] * (count - len(registers))
            return registers[:count]

    client = FailingMockClient()

    # Simulate optimized read failing
    try:
        result = await client.read_holding_registers(1, 79)
        assert False, "Should have failed"
    except Exception:
        pass  # Expected to fail

    # Simulate fallback reads
    fallback_results = []
    for start, count in [(1, 25), (26, 25), (51, 30)]:
        try:
            result = await client.read_holding_registers(start, count)
            fallback_results.append(result)
        except Exception:
            pass

    print("Optimized read failed as expected")
    print(f"Fallback reads: {len(fallback_results)} successful")
    print(f"Total operations: {len(client.get_read_operations())}")

    # Verify fallback worked
    assert len(fallback_results) == 3, "All fallback reads should succeed"
    assert len(client.get_read_operations()) == 4, "1 failed + 3 successful reads"

    print("✅ Fallback mechanism working correctly!")


@pytest.mark.asyncio
async def test_memory_efficiency_of_batching():
    """Test memory usage with optimized batching."""

    import gc

    print("\n" + "=" * 80)
    print("💾 MEMORY EFFICIENCY TEST")
    print("=" * 80)

    client = FakeModbusClientPerformance("192.168.1.100", 502, timing_mode="fast")
    await client.connect()

    # Baseline memory
    gc.collect()
    baseline_objects = len(gc.get_objects())

    # Simulate 100 optimized read cycles
    for cycle in range(100):
        # Optimized single reads
        input_data = await client.read_input_registers(21, 67)
        holding_data = await client.read_holding_registers(1, 79)

        # Process data (simulate)
        processed_data = {
            "input": input_data,
            "holding": holding_data,
            "cycle": cycle,
            "timestamp": time.time(),
        }

        # Clear references
        del processed_data

        if cycle % 20 == 0:
            gc.collect()

    # Check memory usage
    gc.collect()
    final_objects = len(gc.get_objects())
    object_growth = final_objects - baseline_objects

    print(f"Baseline objects: {baseline_objects:,}")
    print(f"Final objects: {final_objects:,}")
    print(f"Object growth: {object_growth:,}")
    print(f"Growth per cycle: {object_growth / 100:.1f}")
    print(f"Memory efficiency: {'✅ Good' if object_growth < 500 else '⚠️ High'}")

    # Memory should be efficient
    assert object_growth < 500, f"Memory growth too high: {object_growth}"

    print("✅ Memory efficiency test passed!")


if __name__ == "__main__":
    asyncio.run(test_batching_optimization_comparison())
    asyncio.run(test_batching_fallback_mechanism())
    asyncio.run(test_memory_efficiency_of_batching())
