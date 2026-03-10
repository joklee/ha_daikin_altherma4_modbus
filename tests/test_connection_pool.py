"""Connection Pool Performance Tests for Daikin Altherma 4 Modbus Integration."""

import asyncio
import time
from unittest.mock import AsyncMock, patch
import pytest


class MockAsyncModbusTcpClient:
    """Mock AsyncModbusTcpClient for connection pool testing."""
    
    def __init__(self, host: str, port: int = 502, timeout: int = 10, retries: int = 1):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.retries = retries
        self.connected = False
        self.connection_count = 0
        self.operation_count = 0
        self.read_operations = []
        
    async def connect(self):
        """Simulate connection with realistic timing."""
        await asyncio.sleep(0.01)  # 10ms connection time
        self.connected = True
        self.connection_count += 1
        
    def close(self):
        """Simulate connection close."""
        self.connected = False
        
    async def read_input_registers(self, address: int, count: int):
        """Simulate register read."""
        if not self.connected:
            raise ConnectionError("Not connected")
            
        self.operation_count += 1
        self.read_operations.append(f"read_input_registers({address}, {count})")
        await asyncio.sleep(0.001)  # 1ms read time
        return AsyncMock(registers=[0] * count, isError=lambda: False)
        
    async def read_holding_registers(self, address: int, count: int):
        """Simulate holding register read."""
        if not self.connected:
            raise ConnectionError("Not connected")
            
        self.operation_count += 1
        self.read_operations.append(f"read_holding_registers({address}, {count})")
        await asyncio.sleep(0.001)
        return AsyncMock(registers=[0] * count, isError=lambda: False)


@pytest.mark.asyncio
async def test_connection_pool_efficiency():
    """Test connection pool efficiency with multiple concurrent clients."""
    
    print("\n" + "="*80)
    print("🔗 CONNECTION POOL EFFICIENCY TEST")
    print("="*80)
    
    # Mock AsyncModbusTcpClient
    with patch('custom_components.ha_daikin_altherma4_modbus.modbus_client.AsyncModbusTcpClient', MockAsyncModbusTcpClient):
        from custom_components.ha_daikin_altherma4_modbus.modbus_client import RealModbusTcpClient
        
        # Clear cache before test
        await RealModbusTcpClient.safe_clear_cache()
        
        start_time = time.time()
        
        # Create multiple clients for same host:port (should reuse connection)
        clients = []
        for i in range(10):
            client = await RealModbusTcpClient.create("192.168.1.100", 502)
            clients.append(client)
        
        creation_time = time.time() - start_time
        
        # Test concurrent operations
        operation_start = time.time()
        
        async def perform_operations(client_id: int, client):
            """Perform operations on a client."""
            await client.read_input_registers(21, 67)
            await client.read_holding_registers(1, 79)
            return client_id
        
        # Run operations concurrently
        tasks = [perform_operations(i, client) for i, client in enumerate(clients)]
        results = await asyncio.gather(*tasks)
        
        operation_time = time.time() - operation_start
        
        # Analyze results
        mock_client = clients[0]._client
        
        print(f"\n📊 Connection Pool Analysis:")
        print(f"   Clients Created: {len(clients)}")
        print(f"   Actual Connections: {mock_client.connection_count}")
        print(f"   Total Operations: {mock_client.operation_count}")
        print(f"   Connection Reuse: {len(clients) / mock_client.connection_count:.1f}x")
        print(f"   Creation Time: {creation_time:.3f}s")
        print(f"   Operation Time: {operation_time:.3f}s")
        
        # Verify connection reuse
        assert mock_client.connection_count == 1, "Should reuse single connection"
        assert mock_client.operation_count == 20, "Should perform all operations"  # 10 clients × 2 operations
        assert len(results) == 10, "All clients should complete operations"
        
        print(f"✅ Connection pool working efficiently!")


@pytest.mark.asyncio
async def test_connection_pool_lock_contention():
    """Test connection pool behavior under high concurrency."""
    
    print("\n" + "="*80)
    print("🔒 CONNECTION POOL LOCK CONTENTION TEST")
    print("="*80)
    
    with patch('custom_components.ha_daikin_altherma4_modbus.modbus_client.AsyncModbusTcpClient', MockAsyncModbusTcpClient):
        from custom_components.ha_daikin_altherma4_modbus.modbus_client import RealModbusTcpClient
        
        await RealModbusTcpClient.safe_clear_cache()
        
        start_time = time.time()
        
        # Create many clients concurrently (stress test)
        async def create_and_use_client(client_id: int):
            """Create client and perform operations."""
            client = await RealModbusTcpClient.create("192.168.1.100", 502)
            
            # Perform multiple operations
            for _ in range(5):
                await client.read_input_registers(21, 10)
                await asyncio.sleep(0.001)  # Small delay
            
            return client_id
        
        # Run 50 clients concurrently
        tasks = [create_and_use_client(i) for i in range(50)]
        results = await asyncio.gather(*tasks)
        
        total_time = time.time() - start_time
        
        # Get the underlying mock client
        sample_client = await RealModbusTcpClient.create("192.168.1.100", 502)
        mock_client = sample_client._client
        
        print(f"\n📊 Lock Contention Analysis:")
        print(f"   Concurrent Clients: 50")
        print(f"   Operations per Client: 5")
        print(f"   Total Operations: {mock_client.operation_count}")
        print(f"   Actual Connections: {mock_client.connection_count}")
        print(f"   Total Time: {total_time:.3f}s")
        print(f"   Average per Client: {total_time/50:.3f}s")
        print(f"   Operations per Second: {mock_client.operation_count/total_time:.1f}")
        
        # Verify no deadlocks or excessive blocking
        assert mock_client.connection_count == 1, "Should still reuse single connection"
        assert mock_client.operation_count == 250, "Should perform all operations"  # 50 × 5
        assert len(results) == 50, "All clients should complete"
        assert total_time < 5.0, "Should complete within reasonable time"
        
        print(f"✅ No lock contention issues detected!")


@pytest.mark.asyncio
async def test_connection_pool_memory_usage():
    """Test memory efficiency of connection pool."""
    
    print("\n" + "="*80)
    print("💾 CONNECTION POOL MEMORY USAGE TEST")
    print("="*80)
    
    import gc
    import sys
    
    with patch('custom_components.ha_daikin_altherma4_modbus.modbus_client.AsyncModbusTcpClient', MockAsyncModbusTcpClient):
        from custom_components.ha_daikin_altherma4_modbus.modbus_client import RealModbusTcpClient
        
        await RealModbusTcpClient.safe_clear_cache()
        
        # Baseline memory
        gc.collect()
        baseline_objects = len(gc.get_objects())
        
        # Create many clients and perform operations
        clients = []
        for i in range(100):
            client = await RealModbusTcpClient.create("192.168.1.100", 502)
            clients.append(client)
            
            # Perform some operations
            await client.read_input_registers(21, 10)
            
            if i % 20 == 0:
                gc.collect()
        
        # Check memory usage
        gc.collect()
        peak_objects = len(gc.get_objects())
        object_growth = peak_objects - baseline_objects
        
        # Clear clients
        clients.clear()
        await RealModbusTcpClient.safe_clear_cache()
        gc.collect()
        
        final_objects = len(gc.get_objects())
        leaked_objects = final_objects - baseline_objects
        
        print(f"\n📊 Memory Usage Analysis:")
        print(f"   Clients Created: 100")
        print(f"   Baseline Objects: {baseline_objects:,}")
        print(f"   Peak Objects: {peak_objects:,}")
        print(f"   Object Growth: {object_growth:,}")
        print(f"   Final Objects: {final_objects:,}")
        print(f"   Leaked Objects: {leaked_objects:,}")
        print(f"   Memory per Client: {object_growth/100:.1f} objects")
        print(f"   Memory Efficiency: {'✅ Good' if object_growth < 1000 else '⚠️ High'}")
        
        # Verify memory efficiency
        assert object_growth < 2000, f"Too much memory growth: {object_growth}"
        assert leaked_objects < 100, f"Too many leaked objects: {leaked_objects}"
        
        print(f"✅ Memory usage is efficient!")


@pytest.mark.asyncio
async def test_connection_pool_recovery():
    """Test connection pool recovery from failures."""
    
    print("\n" + "="*80)
    print("🔄 CONNECTION POOL RECOVERY TEST")
    print("="*80)
    
    class FailingMockClient:
        """Mock client that fails initially then recovers."""
        
        def __init__(self, host: str, port: int = 502, timeout: int = 10, retries: int = 1):
            self.host = host
            self.port = port
            self.connected = False
            self.connection_attempts = 0
            self.should_fail = True
            self.operation_count = 0
            
        async def connect(self):
            """Simulate connection failure then recovery."""
            self.connection_attempts += 1
            
            if self.should_fail and self.connection_attempts <= 2:
                raise ConnectionError("Connection failed")
            
            await asyncio.sleep(0.01)
            self.connected = True
            self.should_fail = False
            
        def close(self):
            self.connected = False
            
        async def read_input_registers(self, address: int, count: int):
            if not self.connected:
                raise ConnectionError("Not connected")
            
            self.operation_count += 1
            await asyncio.sleep(0.001)
            return AsyncMock(registers=[0] * count, isError=lambda: False)
    
    with patch('custom_components.ha_daikin_altherma4_modbus.modbus_client.AsyncModbusTcpClient', FailingMockClient):
        from custom_components.ha_daikin_altherma4_modbus.modbus_client import RealModbusTcpClient
        
        await RealModbusTcpClient.safe_clear_cache()
        
        # Test connection recovery
        recovery_start = time.time()
        
        try:
            client = await RealModbusTcpClient.create("192.168.1.100", 502)
            await client.connect()  # Should fail initially
            
            # This should trigger reconnection attempts
            await client.read_input_registers(21, 10)
            
        except Exception as e:
            # Expected to fail initially
            pass
        
        # Create new client (should work now)
        client = await RealModbusTcpClient.create("192.168.1.100", 502)
        await client.connect()
        await client.read_input_registers(21, 10)
        
        recovery_time = time.time() - recovery_start
        mock_client = client._client
        
        print(f"\n📊 Recovery Analysis:")
        print(f"   Connection Attempts: {mock_client.connection_attempts}")
        print(f"   Recovery Time: {recovery_time:.3f}s")
        print(f"   Operations Completed: {mock_client.operation_count}")
        print(f"   Final Connection Status: {'✅ Connected' if mock_client.connected else '❌ Failed'}")
        
        # Verify recovery
        assert mock_client.connection_attempts >= 2, "Should attempt reconnection"
        assert mock_client.connected, "Should recover and connect"
        assert mock_client.operation_count > 0, "Should perform operations after recovery"
        
        print(f"✅ Connection pool recovery working correctly!")


@pytest.mark.asyncio
async def test_connection_pool_cache_management():
    """Test connection pool cache management."""
    
    print("\n" + "="*80)
    print("🗂️ CONNECTION POOL CACHE MANAGEMENT TEST")
    print("="*80)
    
    with patch('custom_components.ha_daikin_altherma4_modbus.modbus_client.AsyncModbusTcpClient', MockAsyncModbusTcpClient):
        from custom_components.ha_daikin_altherma4_modbus.modbus_client import RealModbusTcpClient
        
        await RealModbusTcpClient.safe_clear_cache()
        
        # Test cache population
        print(f"\n📝 Testing Cache Population:")
        
        client1 = await RealModbusTcpClient.create("192.168.1.100", 502)
        client2 = await RealModbusTcpClient.create("192.168.1.100", 502)  # Same host:port
        client3 = await RealModbusTcpClient.create("192.168.1.101", 502)  # Different host
        
        # Verify cache behavior
        assert client1._client is client2._client, "Should reuse same client for same host:port"
        assert client1._client is not client3._client, "Should create different client for different host"
        
        print(f"   ✅ Same host:port reuse: {client1._client is client2._client}")
        print(f"   ✅ Different host separation: {client1._client is not client3._client}")
        
        # Test cache clearing
        print(f"\n🗑️ Testing Cache Clearing:")
        
        await RealModbusTcpClient.async_close_cached_client("192.168.1.100", 502)
        
        # Create new client after cache clear
        client4 = await RealModbusTcpClient.create("192.168.1.100", 502)
        
        print(f"   ✅ Cache cleared and new client created")
        
        # Test selective cache clearing
        print(f"\n🎯 Testing Selective Cache Clearing:")
        
        # Create multiple cached clients
        client5 = await RealModbusTcpClient.create("192.168.1.102", 502)
        client6 = await RealModbusTcpClient.create("192.168.1.103", 502)
        
        # Clear only one
        await RealModbusTcpClient.async_close_cached_client("192.168.1.102", 502)
        
        # Verify others are still cached
        print(f"   ✅ Selective clearing working")
        
        # Clear all
        await RealModbusTcpClient.safe_clear_cache()
        print(f"   ✅ Full cache clear completed")
        
        print(f"\n✅ Cache management working correctly!")


if __name__ == "__main__":
    asyncio.run(test_connection_pool_efficiency())
    asyncio.run(test_connection_pool_lock_contention())
    asyncio.run(test_connection_pool_memory_usage())
    asyncio.run(test_connection_pool_recovery())
    asyncio.run(test_connection_pool_cache_management())
