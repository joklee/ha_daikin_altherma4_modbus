#!/usr/bin/env python3

import asyncio
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../custom_components'))

from ha_daikin_altherma4_modbus.mock_client import MockModbusTcpClient

def test_mock_client():
    # Test the mock client
    async def run_test():
        client = MockModbusTcpClient("localhost")
        await client.connect()

        # Read some problematic registers
        print("Testing input_37 (address 37):")
        result = await client.read_input_registers(37, 1)
        print(f"Registers array length: {len(result.registers)}")
        print(f"Value: {result.registers[37] if len(result.registers) > 37 else 'Index out of range'}")

        print("\nTesting input_52 (address 52):")
        result = await client.read_input_registers(52, 1)
        print(f"Value: {result.registers[52] if len(result.registers) > 52 else 'Index out of range'}")

        print("\nTesting input_65 (address 65):")
        result = await client.read_input_registers(65, 1)
        print(f"Value: {result.registers[65] if len(result.registers) > 65 else 'Index out of range'}")

        print("\nTesting holding_80 (address 80):")
        result = await client.read_holding_registers(80, 1)
        print(f"Value: {result.registers[80] if len(result.registers) > 80 else 'Index out of range'}")
    
    asyncio.run(run_test())

if __name__ == "__main__":
    test_mock_client()
