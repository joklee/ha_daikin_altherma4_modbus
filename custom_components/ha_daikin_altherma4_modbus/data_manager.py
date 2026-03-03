"""Modbus data management classes for Daikin Altherma 4 integration."""

import logging
import asyncio
import time
from typing import Any
from .const import (
    INPUT_REGISTERS,
    HOLDING_REGISTERS,
    SELECT_REGISTERS,
    HOLDING_SWITCHES,
    DISCRETE_INPUT_SENSORS,
    COIL_SENSORS, CALCULATED_SENSORS
)
from .helper import update_value_if_changed
from .connection_manager import ensure_modbus_connection
from .client_interface import ModbusClientInterface

_LOGGER = logging.getLogger(__name__)

class ModbusDataManager:
    """Handles input register, discrete input, and coil data fetching."""
    
    def __init__(self, host: str, port: int, demo_mode: bool = False):
        self.host = host
        self.port = port
        self.demo_mode = demo_mode
        self.client: ModbusClientInterface | None = None
        self.previous_data = {}
        self.last_triggered = {}
        self._client_initialized = False
        self.coordinator = None  # Reference to coordinator for direct data updates
    
    def _update_coordinator_data(self, register_name: str, value: Any) -> None:
        """Update coordinator data after successful write operation."""
        if self.coordinator:
            if register_name in self.coordinator.data:
                # Update existing data with new value
                self.coordinator.data[register_name]['value'] = value
                
                # Trigger entity refresh by marking data as changed
                self.coordinator.data[register_name]['last_updated'] = time.time()
                
                # Explicitly notify coordinator of data change
                if hasattr(self.coordinator, 'async_set_updated_data'):
                    try:
                        # Create a copy of the data to avoid modifying the original
                        updated_data = self.coordinator.data.copy()
                        self.coordinator.async_set_updated_data(updated_data)
                    except Exception as e:
                        _LOGGER.warning(f"Failed to notify coordinator of data change: {e}")
            else:
                _LOGGER.warning(f"Register {register_name} not found in coordinator data")
    
    @staticmethod
    def _is_modbus_error(response) -> object | bool:
        """Check if Modbus response indicates an error, compatible with both mock and real clients."""
        # Try isError() first (pymodbus standard)
        if hasattr(response, 'isError') and callable(response.isError):
            return response.isError()
        # Fall back to is_error() (mock client)
        elif hasattr(response, 'is_error') and callable(response.is_error):
            return response.is_error()
        # If neither method exists, assume no error
        return False
    
    async def _ensure_connection_and_prepare_data(self) -> dict:
        """Shared method for connection setup and data preparation."""
        if self.client is None:
            _LOGGER.debug(f"Creating Modbus client for {self.host}:{self.port}")
        
        try:
            self.client = await ensure_modbus_connection(self.client, self.host, self.port, self.demo_mode)
        except Exception as e:
            _LOGGER.error(f"Failed to establish Modbus connection to {self.host}:{self.port}: {e}")
            if self.demo_mode:
                _LOGGER.info("In demo mode, creating mock client as fallback")
                from .mock_client import MockModbusTcpClient
                self.client = MockModbusTcpClient(self.host, self.port)
                try:
                    await self.client.connect()
                    _LOGGER.info("Successfully created fallback mock client in demo mode")
                except Exception as mock_e:
                    _LOGGER.error(f"Even mock client creation failed: {mock_e}")
                    self.client = None
            else:
                _LOGGER.error(f"Real mode connection failed to {self.host}:{self.port}")
                _LOGGER.info("Possible solutions:")
                _LOGGER.info("1. Check if the Daikin device is powered on")
                _LOGGER.info("2. Verify the IP address and port (default: 502)")
                _LOGGER.info("3. Check network connectivity to the device")
                _LOGGER.info("4. Ensure Modbus TCP is enabled on the device")
                _LOGGER.info("5. Try enabling demo mode for testing")
                self.client = None
        
        # Return empty dict if no connection, but don't crash
        return {}
    
    async def fetch_input_registers_data(self) -> dict:
        """Fetch only Input Registers data."""
        start_time = time.time()
        data = await self._ensure_connection_and_prepare_data()
        
        # Only try to fetch if we have a connection
        if self.client is not None:
            # Fetch Input Registers (now includes binary sensors)
            input_data = await self._fetch_input_registers()
            data.update(input_data)
        else:
            _LOGGER.warning("Skipping input registers fetch - no Modbus connection available")
        
        # Store previous data for change detection (merge instead of overwrite)
        self.previous_data.update(data)
        
        total_time = time.time() - start_time
        _LOGGER.debug(f"Input Registers processed in {total_time:.3f}s")
        
        return data
    
    async def fetch_discrete_inputs_data(self) -> dict:
        """Fetch only Discrete Inputs data."""
        start_time = time.time()
        data = await self._ensure_connection_and_prepare_data()
        
        # Only try to fetch if we have a connection
        if self.client is not None:
            # Fetch Discrete Inputs
            discrete_data = await self._fetch_discrete_inputs()
            data.update(discrete_data)
        else:
            _LOGGER.warning("Skipping discrete inputs fetch - no Modbus connection available")

        # Update last triggered for binary sensors (now part of discrete registers)
        self._update_last_triggered(data)

        # Store previous data for change detection (merge instead of overwrite)
        self.previous_data.update(data)
        
        total_time = time.time() - start_time
        _LOGGER.debug(f"Discrete Inputs processed in {total_time:.3f}s")
        
        return data
    
    async def fetch_coils_data(self) -> dict:
        """Fetch only Coils data."""
        start_time = time.time()
        data = await self._ensure_connection_and_prepare_data()
        
        # Only try to fetch if we have a connection
        if self.client is not None:
            # Fetch Coils
            coil_data = await self._fetch_coils()
            data.update(coil_data)
        else:
            _LOGGER.warning("Skipping coils fetch - no Modbus connection available")
        
        # Store previous data for change detection (merge instead of overwrite)
        self.previous_data.update(data)
        
        total_time = time.time() - start_time
        _LOGGER.debug(f"Coils processed in {total_time:.3f}s")
        
        return data
    
    async def fetch_holding_registers_data(self) -> dict:
        """Fetch only Holding Registers data."""
        start_time = time.time()
        data = await self._ensure_connection_and_prepare_data()
        
        # Only try to fetch if we have a connection
        if self.client is not None:
            # Fetch Holding Registers
            holding_data = await self._fetch_holding_data()
            data.update(holding_data)
        else:
            _LOGGER.warning("Skipping holding registers fetch - no Modbus connection available")
        
        # Store previous data for change detection (merge instead of overwrite)
        self.previous_data.update(data)
        
        total_time = time.time() - start_time
        _LOGGER.debug(f"Holding Registers processed in {total_time:.3f}s")
        
        return data
    
    async def refresh_holding_registers(self) -> dict:
        """Refresh holding registers for interval updates."""
        start_time = time.time()
        data = await self._ensure_connection_and_prepare_data()
        
        if self.client is not None:
            holding_data = await self._fetch_holding_data()
            data.update(holding_data)
            
            _LOGGER.debug(f"Holding Registers refresh: {time.time() - start_time:.3f}s")
        else:
            _LOGGER.warning("Skipping holding registers refresh - no Modbus connection available")
        
        return data
    
    async def refresh_coils(self) -> dict:
        """Refresh coils for interval updates."""
        start_time = time.time()
        data = await self._ensure_connection_and_prepare_data()
        
        if self.client is not None:
            coil_data = await self._fetch_coils()
            data.update(coil_data)
            
            _LOGGER.debug(f"Coils Refresh: {time.time() - start_time:.3f}s")
        else:
            _LOGGER.warning("Skipping coils refresh - no Modbus connection available")
        
        return data
    
    async def refresh_all_data(self) -> dict:
        """Refresh all Modbus data for interval updates."""
        start_time = time.time()
        data = await self._ensure_connection_and_prepare_data()
        
        # Only try to fetch if we have a connection
        if self.client is not None:
            register_data = await self._fetch_all_register_data()
            data.update(register_data)
            _LOGGER.debug(f"Register refresh: Input + Discrete + Coils + Holding = {time.time() - start_time:.3f}s")
        else:
            _LOGGER.warning("Skipping register refresh - no Modbus connection available")
        
        return data
    
    async def _fetch_all_register_data(self) -> dict:
        """Common method to fetch all Modbus register data."""
        data = {}
        
        # Fetch Input Registers (now includes binary sensors)
        input_data = await self._fetch_input_registers()
        data.update(input_data)
        
        # Add delay between requests
        await asyncio.sleep(0.1)
        
        # Fetch Discrete Inputs
        discrete_data = await self._fetch_discrete_inputs()
        data.update(discrete_data)
        
        # Add delay between requests
        await asyncio.sleep(0.1)
        
        # Fetch Coils
        coil_data = await self._fetch_coils()
        data.update(coil_data)
        
        # Add delay between requests
        await asyncio.sleep(0.1)
        
        # Fetch Holding Registers
        holding_data = await self._fetch_holding_data()
        data.update(holding_data)
        
        return data
    
    async def fetch_all_data(self) -> dict:
        """Fetch all Modbus data and return structured data dictionary."""
        start_time = time.time()
        data = await self._ensure_connection_and_prepare_data()
        
        # Only try to fetch if we have a connection
        if self.client is not None:
            register_data = await self._fetch_all_register_data()
            data.update(register_data)
        else:
            _LOGGER.warning("Skipping all register fetches - no Modbus connection available")
        
        # Update last triggered for binary sensors (now part of input registers)
        self._update_last_triggered(data)
        
        # Store previous data for change detection (merge instead of overwrite)
        self.previous_data.update(data)
        
        total_time = time.time() - start_time
        _LOGGER.debug(f"All registers read in {total_time:.3f}s")
        
        return data
    
    async def _fetch_input_registers(self) -> dict:
        """Fetch all input registers in blocks."""
        data = {}
        start_time = time.time()
        
        if self.client is None:
            _LOGGER.error("Modbus client is None, cannot read input registers")
            return data
        
        try:
            # Block 1: Addresses 21-53 (33 registers)
            block_start = time.time()
            ir1 = await self.client.read_input_registers(21, 33)
            block_time = time.time() - block_start
            _LOGGER.debug(f"Input Register Block 1 read in {block_time:.3f}s")
            
            if not self._is_modbus_error(ir1):
                data.update(self._process_input_register_block(ir1, INPUT_REGISTERS, 21, 53, 21))
            else:
                _LOGGER.error("Input Register Block 1 read failed")
        except Exception as e:
            _LOGGER.warning(f"Could not read Input Register Block 1: {e}")
        
        try:
            # Block 2: Addresses 54-87 (34 registers)
            block_start = time.time()
            ir2 = await self.client.read_input_registers(54, 34)
            block_time = time.time() - block_start
            _LOGGER.debug(f"Input Register Block 2 read in {block_time:.3f}s")
            
            if not self._is_modbus_error(ir2):
                data.update(self._process_input_register_block(ir2, INPUT_REGISTERS, 54, 87, 54))
            else:
                _LOGGER.error("Input Register Block 2 read failed")
        except Exception as e:
            _LOGGER.warning(f"Could not read Input Register Block 2: {e}")
        
        total_time = time.time() - start_time
        _LOGGER.debug(f"Input Registers fully read in {total_time:.3f}s")
        
        return data
    
    @staticmethod
    def _process_register_block(register_data, register_list, min_address, max_address, offset,
                                default_input_type, register_description) -> dict:
        """Process a block of registers with common logic."""
        data = {}
        for item in register_list:
            address = item["address"]
            input_type = item.get("input_type", default_input_type)
            register_name = item.get("register_name")
            if min_address <= address <= max_address:  # In this block
                try:
                    raw_value = register_data.registers[address]
                except IndexError as e:
                    _LOGGER.error(f"IndexError accessing register {address}: {e}, array_len={len(register_data.registers)}")
                    raise
                
                # Let caller handle special processing (enum mapping, scaling, etc.)
                # Use register_name as key instead of unique_id
                data[register_name] = {
                    "raw_value": raw_value,
                    "input_type": input_type,
                    "address": address,
                    "description": f"{register_description} {address}",
                    "item": item
                }
        
        return data
    
    def _process_input_register_block(self, register_data, register_list, min_address, max_address, offset) -> dict:
        """Process a block of input registers with common logic."""
        processed_data = self._process_register_block(
            register_data, register_list, min_address, max_address, offset, "input", "Input Register"
        )
        
        data = {}
        for register_name, processed_item in processed_data.items():  # Changed from unique_id to register_name
            raw_value = processed_item["raw_value"]
            input_type = processed_item["input_type"]
            address = processed_item["address"]
            description = processed_item["description"]
            item = processed_item["item"]
            
            # Handle enum mapping
            if item.get("enum_map"):
                if raw_value == 32766 and len(item["enum_map"]) <= 2:
                    # Skip entity if value is 32766 (No error/Normal state) and enum is simple
                    continue
                # For sensors with enum_map, store raw value and let sensor handle mapping
                data[register_name] = update_value_if_changed(  # Changed from unique_id to register_name
                    register_name, raw_value, self.previous_data,  # Changed from unique_id to register_name
                    description,
                    input_type=input_type,
                    address=address
                )
            else:
                # Apply scaling for non-enum input registers
                data[register_name] = ModbusDataManager._apply_register_processing(
                    register_name, processed_item, self.previous_data, include_scale=False
                )
        
        return data
    
    def _process_bit_sensors(self, result, data: dict, sensor_list, sensor_type: str) -> None:
        """Process bit-based sensors (discrete inputs or coils) from Modbus result."""
        for item in sensor_list:
            address = item["address"]
            input_type = item.get("input_type", sensor_type)
            register_name = item.get("register_name")

            if address < len(result.bits):
                raw_value = 1 if result.bits[address] else 0
                
                # Use register_name as key instead of unique_id
                data[register_name] = update_value_if_changed(
                    register_name, raw_value, self.previous_data,
                    f"{sensor_type.title()} {address}",
                    input_type=input_type,
                    address=address
                )
            else:
                _LOGGER.warning(f"{sensor_type.title()} {address} nicht im gelesenen Bereich ({len(result.bits)} Bits)")

    def _process_discrete_input_sensors(self, di_result, data: dict) -> None:
        """Process discrete input sensors from Modbus result."""
        self._process_bit_sensors(di_result, data, DISCRETE_INPUT_SENSORS, "discrete_input")
    
    async def _fetch_discrete_inputs(self) -> dict:
        """Fetch all discrete inputs."""
        data = {}
        start_time = time.time()
        
        if self.client is None:
            _LOGGER.error("Modbus client is None, cannot read discrete inputs")
            return data
        
        try:
            read_start = time.time()
            di = await self.client.read_discrete_inputs(1, 26)
            read_time = time.time() - read_start
            _LOGGER.debug(f"Discrete Inputs (30 bits) read in {read_time:.3f}s")
            
            if not self._is_modbus_error(di):
                self._process_discrete_input_sensors(di, data)
            else:
                # Provide specific error information for Modbus exceptions
                error_msg = str(di)
                if "exception_code=2" in error_msg:
                    _LOGGER.warning("Device does not support discrete inputs (Illegal data address)")
                    _LOGGER.info("This Daikin device does not implement discrete input registers")
                elif "exception_code=1" in error_msg:
                    _LOGGER.warning("Device does not support discrete inputs (Illegal function)")
                    _LOGGER.info("This Daikin device does not implement the discrete input function code")
                else:
                    _LOGGER.warning(f"Device does not support discrete inputs or read failed: {di}")
                _LOGGER.info("Skipping discrete inputs - device may not support this register type")
        except Exception as e:
            _LOGGER.warning(f"Could not read Discrete Inputs: {e}")
            # If connection fails, try to re-establish and retry once
            try:
                _LOGGER.info("Attempting to re-establish connection and retry discrete inputs")
                self.client = await ensure_modbus_connection(None, self.host, self.port, self.demo_mode)
                if self.client:
                    di_retry = await self.client.read_discrete_inputs(1, 26)
                    if not self._is_modbus_error(di_retry):
                        self._process_discrete_input_sensors(di_retry, data)
                        _LOGGER.info("Successfully retried discrete inputs after reconnection")
                    else:
                        _LOGGER.warning(f"Discrete inputs retry also failed - device may not support this register type: {di_retry}")
            except Exception as retry_e:
                _LOGGER.warning(f"Retry attempt for discrete inputs failed: {retry_e}")
        
        total_time = time.time() - start_time
        _LOGGER.debug(f"Discrete Inputs fully read in {total_time:.3f}s")
        
        return data
    
    async def _fetch_coils(self) -> dict:
        """Fetch all coils."""
        data = {}
        start_time = time.time()
        
        if self.client is None:
            _LOGGER.error("Modbus client is None, cannot read coils")
            return data
        
        try:
            read_start = time.time()
            cr = await self.client.read_coils(1, 3)
            read_time = time.time() - read_start
            _LOGGER.debug(f"Coils (20 bits) read in {read_time:.3f}s")
            
            if not self._is_modbus_error(cr):
                self._process_bit_sensors(cr, data, COIL_SENSORS, "coil")
            else:
                # Provide specific error information for Modbus exceptions
                error_msg = str(cr)
                if "exception_code=2" in error_msg:
                    _LOGGER.warning("Device does not support coils (Illegal data address)")
                    _LOGGER.info("This Daikin device does not implement coil registers")
                elif "exception_code=1" in error_msg:
                    _LOGGER.warning("Device does not support coils (Illegal function)")
                    _LOGGER.info("This Daikin device does not implement the coil function code")
                else:
                    _LOGGER.warning(f"Device does not support coils or read failed: {cr}")
                _LOGGER.info("Skipping coils - device may not support this register type")
        except Exception as e:
            _LOGGER.warning(f"Could not read Coils: {e}")
            # If connection fails, try to re-establish and retry once
            try:
                _LOGGER.info("Attempting to re-establish connection and retry coils")
                self.client = await ensure_modbus_connection(None, self.host, self.port, self.demo_mode)
                if self.client:
                    cr_retry = await self.client.read_coils(1, 3)
                    if not self._is_modbus_error(cr_retry):
                        self._process_bit_sensors(cr_retry, data, COIL_SENSORS, "coil")
                        _LOGGER.info("Successfully retried coils after reconnection")
                    else:
                        _LOGGER.warning(f"Coils retry also failed - device may not support this register type: {cr_retry}")
            except Exception as retry_e:
                _LOGGER.warning(f"Retry attempt for coils failed: {retry_e}")
        
        total_time = time.time() - start_time
        _LOGGER.debug(f"Coils fully read in {total_time:.3f}s")
        
        return data

    async def write_holding_register(self, register_name: str, value: int) -> Any:
        """Write to a holding register by name (e.g., 'holding_3' -> address 3)."""
        if self.client is None:
            _LOGGER.error("Modbus client is None, cannot write register")
            return None
        
        try:
          address = int(register_name.split("_")[1])
        except (ValueError, IndexError):
            _LOGGER.error(f"Invalid address name format: {register_name}")
            return None
        
        try:
            result = await self.client.write_holding_register(address, value)
            if self._is_modbus_error(result):
                _LOGGER.error(f"Failed to write register {register_name} (address {address}) with value {value}: {result}")
                return None
            else:
                _LOGGER.debug(f"Successfully wrote register {register_name} (address {address}) with value {value}")
                # Update coordinator data directly instead of refreshing
                self._update_coordinator_data(register_name, value)
                return result
        except Exception as e:
            _LOGGER.error(f"Exception writing register {register_name} (address {address}) with value {value}: {e}")
            return None
    
    async def write_coil_register(self, register_name: str, value: bool) -> Any:
        """Write to a coil register by name (e.g., 'coil_1' -> address 1)."""
        if self.client is None:
            _LOGGER.error("Modbus client is None, cannot write coil")
            return None
        
        # Extract numeric address from string
        if isinstance(register_name, str) and register_name.startswith("coil_"):
            try:
                address = int(register_name.split("_")[1])
            except (ValueError, IndexError):
                _LOGGER.error(f"Invalid address name format: {register_name}")
                return None
        elif isinstance(register_name, int):
            # Direct integer address
            address = register_name
        else:
            _LOGGER.error(f"Invalid address format: {register_name}")
            return None
        
        try:
            result = await self.client.write_coil_register(address, value)
            if self._is_modbus_error(result):
                _LOGGER.error(f"Failed to write coil {register_name} (address {address}) with value {value}: {result}")
                return None
            else:
                _LOGGER.debug(f"Successfully wrote coil {register_name} (address {address}) with value {value}")
                # Update coordinator data directly instead of refreshing
                self._update_coordinator_data(register_name, value)
                return result
        except Exception as e:
            _LOGGER.error(f"Exception writing coil {register_name} (address {address}) with value {value}: {e}")
            return None
    
    async def _refresh_single_holding_register(self, register_id: str, address: int) -> dict:
        """Refresh a single holding register."""
        if self.client is None:
            _LOGGER.error("Modbus client is None, cannot read holding register")
            return {}
        
        try:
            # Read single holding register
            result = await self.client.read_holding_registers(address, 1)
            if self._is_modbus_error(result):
                _LOGGER.error(f"Failed to read holding register {address}: {result}")
                return {}

            raw_value = result.registers[address] if len(result.registers) > address else 0
            data = {
                "value": raw_value,
                "input_type": "holding",
                "address": address
            }
            
            _LOGGER.debug(f"Refreshed holding register {register_id}: {raw_value}")
            return {register_id: data}
            
        except Exception as e:
            _LOGGER.error(f"Exception reading holding register {address}: {e}")
            return {}
    
    async def _refresh_single_coil(self, register_id: str, address: int) -> dict:
        """Refresh a single coil."""
        if self.client is None:
            _LOGGER.error("Modbus client is None, cannot read coil")
            return {}
        
        try:
            # Read single coil
            result = await self.client.read_coils(address, 1)
            if self._is_modbus_error(result):
                _LOGGER.error(f"Failed to read coil {address}: {result}")
                return {}
            
            # Update data with new value
            raw_value = 1 if result.bits[0] else 0
            data = {
                "value": raw_value,
                "input_type": "coil",
                "address": address
            }
            
            _LOGGER.debug(f"Refreshed coil {register_id}: {raw_value}")
            return {register_id: data}
            
        except Exception as e:
            _LOGGER.error(f"Exception reading coil {address}: {e}")
            return {}
    
    def _update_last_triggered(self, data: dict):
        """Update last triggered timestamps for binary sensors."""
        from homeassistant.util import dt as dt_util

        for item in CALCULATED_SENSORS:
            if item.get("trigger_register_name") is not None:
                register_name = item.get("register_name")
                trigger_register_name = item.get("trigger_register_name")

                current_data = data.get(trigger_register_name, {})
                current_val = current_data.get("value")
                previous_data = self.previous_data.get(trigger_register_name, {})
                previous_val = previous_data.get("value")

                is_on = current_val == 1
                was_on = previous_val == 1 if previous_val is not None else False
                if is_on and not was_on:
                    self.last_triggered[register_name] = dt_util.now()

                # Add to data
                if register_name in self.last_triggered:
                    data[register_name] = {
                        "value": self.last_triggered[register_name],
                        "input_type": "calculated",
                        "register_name": register_name
                    }
                else:
                    # No trigger yet, provide default structure
                    data[register_name] = {
                        "value": None,
                        "input_type": "calculated", 
                        "register_name": register_name
                    }

    async def _fetch_holding_data(self) -> dict:
        """Fetch all holding registers in blocks."""
        data = {}
        start_time = time.time()
        
        if self.client is None:
            _LOGGER.error("Modbus client is None, cannot read holding registers")
            return data
        
        # Define the 3 blocks: (start_address, count, min_address, max_address, offset, block_name, is_optional)
        blocks = [
            (1, 25, 1, 25, 1, "Block 1", False),    # Addresses 1-25 - required
            (26, 25, 26, 50, 26, "Block 2", False), # Addresses 26-50 - required  
            (51, 30, 51, 80, 51, "Block 3", True),  # Addresses 51-80 - optional
        ]
        
        for start_addr, count, min_addr, max_addr, offset, block_name, is_optional in blocks:
            block_data = await self._read_holding_register_block(
                start_addr, count, min_addr, max_addr, offset, block_name, is_optional
            )
            data.update(block_data)
            
            # Add delay between blocks to prevent overwhelming the device
            await asyncio.sleep(0.2)
        
        total_time = time.time() - start_time
        _LOGGER.debug(f"Holding Registers fully read in {total_time:.3f}s")
        
        return data
    
    async def _read_holding_register_block(self, start_address: int, count: int, 
                                         min_address: int, max_address: int, offset: int,
                                         block_name: str, is_optional: bool) -> dict:
        """Read a single holding register block with retry logic."""
        data = {}
        
        try:
            block_start = time.time()
            result = await self.client.read_holding_registers(start_address, count)
            block_time = time.time() - block_start
            _LOGGER.debug(f"Holding Register {block_name} ({count} registers) read in {block_time:.3f}s")
            
            if not self._is_modbus_error(result):
                # Verarbeite HOLDING_REGISTERS, SELECT_REGISTERS und HOLDING_SWITCHES
                all_holding_registers = HOLDING_REGISTERS + SELECT_REGISTERS + HOLDING_SWITCHES
                data.update(self._process_holding_register_block(result, all_holding_registers, min_address, max_address, offset))
            else:
                if is_optional:
                    _LOGGER.warning(f"Device does not support holding register {block_name} (addresses {min_address}-{max_address}): {result}")
                    _LOGGER.info(f"Skipping holding register {block_name} - device may not support these address ranges")
                else:
                    _LOGGER.error(f"Holding Register {block_name} read failed: {result}")
                    
        except Exception as e:
            _LOGGER.warning(f"Could not read Holding Register {block_name}: {e}")
            # If connection fails, try to re-establish and retry once
            try:
                _LOGGER.info(f"Attempting to re-establish connection and retry holding register {block_name}")
                self.client = await ensure_modbus_connection(None, self.host, self.port, self.demo_mode)
                if self.client:
                    retry_result = await self.client.read_holding_registers(start_address, count)
                    if not self._is_modbus_error(retry_result):
                        # Process HOLDING_REGISTERS, SELECT_REGISTERS und HOLDING_SWITCHES
                        all_holding_registers = HOLDING_REGISTERS + SELECT_REGISTERS + HOLDING_SWITCHES
                        data.update(self._process_holding_register_block(retry_result, all_holding_registers, min_address, max_address, offset))
                        _LOGGER.info(f"Successfully retried holding register {block_name} after reconnection")
                    else:
                        if is_optional:
                            _LOGGER.warning(f"Holding Register {block_name} retry also failed - device may not support these addresses: {retry_result}")
                        else:
                            _LOGGER.warning(f"Holding Register {block_name} retry also failed: {retry_result}")
            except Exception as retry_e:
                _LOGGER.warning(f"Retry attempt for Holding Register {block_name} failed: {retry_e}")
        
        return data
    
    @staticmethod
    def _apply_register_processing(register_name, processed_item, previous_data, include_scale=True):
        """Apply scaling and unavailable value handling to register data."""
        raw_value = processed_item["raw_value"]
        input_type = processed_item["input_type"]
        address = processed_item["address"]
        description = processed_item["description"]
        item = processed_item["item"]
        
        # Apply scaling
        if "scale" in item:
            # Check for unavailable value before scaling
            if raw_value == 32765 or raw_value == 32766:
                return update_value_if_changed(
                    register_name, raw_value, previous_data,
                    description,
                    input_type=input_type,
                    address=address,
                    scale=item["scale"]  # Store scale in data
                )
            else:
                scaled_value = raw_value * item["scale"]
                # Round to 2 decimal places to avoid float precision issues
                scaled_value = round(scaled_value, 2)
                return update_value_if_changed(
                    register_name, scaled_value, previous_data,
                    description,
                    input_type=input_type,
                    address=address,
                    scale=item["scale"]  # Store scale in data
                )
        else:
            kwargs = {
                "register_name": register_name,
                "value": raw_value,
                "previous_data": previous_data,
                "description": description,
                "input_type": input_type,
                "address": address
            }
            if include_scale:
                kwargs["scale"] = 1  # Default scale
            return update_value_if_changed(**kwargs)
    
    def _process_holding_register_block(self, register_data, register_list, min_address, max_address, offset) -> dict:
        """Process a block of holding registers with common logic."""
        processed_data = self._process_register_block(
            register_data, register_list, min_address, max_address, offset, "holding", "Holding Register"
        )
        
        data = {}
        for register_name, processed_item in processed_data.items():
            data[register_name] = ModbusDataManager._apply_register_processing(
                register_name, processed_item, self.previous_data
            )
        
        return data
