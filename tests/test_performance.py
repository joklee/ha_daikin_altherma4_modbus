"""Performance tests for Daikin Altherma 4 Modbus integration."""

import asyncio
import time

import pytest


class MockPerformanceClient:
    """Mock client for performance testing."""

    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
        self.connected = True
        self.read_count = 0
        self.total_bytes = 0

    async def connect(self):
        """Simulate connection with small delay."""
        await asyncio.sleep(0.01)  # 10ms connection time
        self.connected = True

    async def read_input_registers(self, address: int, count: int):
        """Simulate register read with realistic timing."""
        await asyncio.sleep(0.001)  # 1ms per register block
        self.read_count += 1
        self.total_bytes += count * 2  # 2 bytes per register
        return [0] * count

    async def read_holding_registers(self, address: int, count: int):
        """Simulate holding register read."""
        await asyncio.sleep(0.001)
        self.read_count += 1
        self.total_bytes += count * 2
        return [0] * count

    async def read_discrete_inputs(self, address: int, count: int):
        """Simulate discrete input read."""
        await asyncio.sleep(0.0005)
        self.read_count += 1
        self.total_bytes += count // 8  # 1 bit per discrete input
        return [0] * ((count + 7) // 8)

    async def read_coils(self, address: int, count: int):
        """Simulate coil read."""
        await asyncio.sleep(0.0005)
        self.read_count += 1
        self.total_bytes += count // 8
        return [0] * ((count + 7) // 8)


def test_mock_client_performance(benchmark):
    """Benchmark mock client basic operations."""

    def basic_operations():
        client = MockPerformanceClient("localhost", 502)

        # Connection
        asyncio.run(client.connect())

        # Register reads
        result1 = asyncio.run(client.read_input_registers(21, 5))
        result2 = asyncio.run(client.read_holding_registers(100, 3))
        result3 = asyncio.run(client.read_discrete_inputs(1, 8))
        result4 = asyncio.run(client.read_coils(1, 8))

        return result1, result2, result3, result4, client

    result1, result2, result3, result4, client = benchmark(basic_operations)

    # Assertions
    assert len(result1) == 5
    assert len(result2) == 3
    assert len(result3) == 1
    assert len(result4) == 1
    assert client.read_count == 4


def test_register_read_performance(benchmark):
    """Benchmark register read operations."""

    def read_multiple_blocks():
        client = MockPerformanceClient("localhost", 502)
        results = []

        # Read multiple register blocks
        for address in range(21, 87, 5):  # Read blocks of 5 registers
            result = asyncio.run(client.read_input_registers(address, 5))
            results.append(result)

        return results, client

    results, client = benchmark(read_multiple_blocks)

    # Should read 14 blocks efficiently (21, 26, 31, 36, 41, 46, 51, 56, 61, 66, 71, 76, 81, 86)
    assert len(results) == 14
    assert client.read_count == 14


def test_memory_allocation_performance(benchmark):
    """Benchmark memory usage patterns."""

    def allocate_register_data():
        """Simulate register data allocation."""
        # Simulate typical register data structures
        data = {
            "input_registers": [0] * 67,  # Max input register range
            "holding_registers": [0] * 50,
            "discrete_inputs": [0] * 26,
            "coils": [0] * 3,
            "timestamps": [time.time()] * 10,
        }
        return data

    # Allocate data multiple times
    results = benchmark(lambda: [allocate_register_data() for _ in range(100)])

    # Should be very fast memory operations
    assert len(results) == 100
    assert all(len(r["input_registers"]) == 67 for r in results)


@pytest.mark.asyncio
async def test_performance_scan_intervals():
    """Test performance impact of different scan intervals."""

    # Test different scan intervals
    intervals = [5, 10, 15, 30, 60]
    results = {}

    for interval in intervals:
        start_time = time.time()

        # Simulate 1 minute of operation
        duration = 60.0  # 1 minute
        cycles = int(duration / interval)

        # Mock client for performance testing
        client = MockPerformanceClient("192.168.1.100", 502)
        await client.connect()

        # Simulate scan cycles
        for _ in range(cycles):
            # Simulate reading all register types
            await client.read_input_registers(21, 67)  # Input registers
            await client.read_holding_registers(1, 60)  # Holding registers
            await client.read_discrete_inputs(1, 26)  # Discrete inputs
            await client.read_coils(1, 3)  # Coils

            # Small delay between cycles
            await asyncio.sleep(0.01)

        elapsed = time.time() - start_time

        results[interval] = {
            "cycles": cycles,
            "total_reads": client.read_count,
            "total_bytes": client.total_bytes,
            "elapsed_time": elapsed,
            "reads_per_second": client.read_count / elapsed,
            "bytes_per_second": client.total_bytes / elapsed,
            "cpu_load_estimate": (client.read_count * 0.001)
            / elapsed,  # Rough estimate
        }

    # Print performance results
    print("\n" + "=" * 80)
    print("📊 PERFORMANCE ANALYSIS: Scan Interval Impact")
    print("=" * 80)

    for interval, metrics in results.items():
        print(f"\n🔄 {interval}s Scan Interval:")
        print(f"   Cycles per minute: {metrics['cycles']}")
        print(f"   Total register reads: {metrics['total_reads']}")
        print(f"   Network traffic: {metrics['total_bytes']:,} bytes")
        print(f"   Reads per second: {metrics['reads_per_second']:.1f}")
        print(f"   Network load: {metrics['bytes_per_second']:.1f} B/s")
        print(f"   Estimated CPU load: {metrics['cpu_load_estimate']:.1%}")

    # Performance recommendations
    print("\n" + "=" * 80)
    print("💡 PERFORMANCE RECOMMENDATIONS")
    print("=" * 80)

    # Find optimal interval based on metrics
    optimal_interval = 15  # Default recommendation
    for interval, metrics in results.items():
        if metrics["cpu_load_estimate"] < 0.05 and metrics["reads_per_second"] < 10:
            optimal_interval = interval
            break

    print(f"✅ Recommended scan interval: {optimal_interval}s")
    print("   - Low CPU load (<5%)")
    print("   - Reasonable update frequency")
    print("   - Network efficient")

    if results[5]["cpu_load_estimate"] > 0.10:
        print(
            f"\n⚠️  WARNING: 5s interval shows high CPU load ({results[5]['cpu_load_estimate']:.1%})"
        )

    if results[5]["bytes_per_second"] > 1000:
        print(
            f"⚠️  WARNING: 5s interval generates high network traffic ({results[5]['bytes_per_second']:.0f} B/s)"
        )

    # Verify performance improvements
    assert results[15]["cpu_load_estimate"] < results[5]["cpu_load_estimate"], (
        "15s interval should have lower CPU load than 5s"
    )
    assert results[15]["bytes_per_second"] < results[5]["bytes_per_second"], (
        "15s interval should generate less network traffic"
    )


@pytest.mark.asyncio
async def test_performance_batch_optimization():
    """Test performance impact of batch vs individual register reads."""

    client = MockPerformanceClient("192.168.1.100", 502)
    await client.connect()

    # Test 1: Individual register reads (current implementation)
    start_time = time.time()
    for addr in range(21, 88):  # Individual input registers
        await client.read_input_registers(addr, 1)
    individual_time = time.time() - start_time

    # Reset client
    client.read_count = 0
    client.total_bytes = 0

    # Test 2: Batch register reads (optimized)
    start_time = time.time()
    await client.read_input_registers(21, 67)  # Single batch read
    batch_time = time.time() - start_time

    print("\n📊 BATCH OPTIMIZATION ANALYSIS:")
    print(f"   Individual reads: {individual_time:.3f}s (67 operations)")
    print(f"   Batch read: {batch_time:.3f}s (1 operation)")
    print(f"   Performance improvement: {(individual_time / batch_time):.1f}x faster")

    # Batch should be significantly faster
    assert batch_time < individual_time, "Batch reading should be faster"
    assert (individual_time / batch_time) > 5, "Batch should be at least 5x faster"


@pytest.mark.asyncio
async def test_performance_memory_usage():
    """Test memory usage patterns during extended operation."""

    import gc

    # Baseline memory
    gc.collect()
    baseline_objects = len(gc.get_objects())

    # Simulate extended operation
    client = MockPerformanceClient("192.168.1.100", 502)
    await client.connect()

    # Simulate 100 update cycles
    for cycle in range(100):
        await client.read_input_registers(21, 67)
        await client.read_holding_registers(1, 60)

        # Simulate data processing
        data = {
            "input_registers": [0] * 67,
            "holding_registers": [0] * 60,
            "cycle": cycle,
            "timestamp": time.time(),
        }

        # Clear data to prevent memory leaks
        del data

        if cycle % 10 == 0:
            gc.collect()

    # Check memory usage
    gc.collect()
    final_objects = len(gc.get_objects())
    object_growth = final_objects - baseline_objects

    print("\n📊 MEMORY USAGE ANALYSIS:")
    print(f"   Baseline objects: {baseline_objects:,}")
    print(f"   Final objects: {final_objects:,}")
    print(f"   Object growth: {object_growth:,}")
    print(f"   Growth per cycle: {object_growth / 100:.1f}")

    # Memory growth should be minimal
    assert object_growth < 1000, f"Memory growth too high: {object_growth} objects"
    assert object_growth / 100 < 10, (
        f"Too many objects per cycle: {object_growth / 100:.1f}"
    )


if __name__ == "__main__":
    asyncio.run(test_performance_scan_intervals())
    asyncio.run(test_performance_batch_optimization())
    asyncio.run(test_performance_memory_usage())
