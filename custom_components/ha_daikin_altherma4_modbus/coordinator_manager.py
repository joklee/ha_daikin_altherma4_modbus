"""Coordinator manager to handle multiple coordinators with different intervals."""
import logging
from homeassistant.core import HomeAssistant
from .coordinator import DaikinAlthermaNormalCoordinator, DaikinAlthermaSlowCoordinator

_LOGGER = logging.getLogger(__name__)

class CoordinatorManager:
    """Manages multiple coordinators and ensures they run independently."""
    
    def __init__(
        self,
        hass: HomeAssistant,
        host: str,
        port: int,
        normal_interval: int = 10,
        slow_interval: int = 600,
        demo_mode: bool = False
    ):
        """Initialize the coordinator manager."""
        self.hass = hass
        self.host = host
        self.port = port
        self.demo_mode = demo_mode
        
        # Create coordinators
        self.normal_coordinator = DaikinAlthermaNormalCoordinator(
            hass, host, port, normal_interval, demo_mode
        )
        self.slow_coordinator = DaikinAlthermaSlowCoordinator(
            hass, host, port, slow_interval, demo_mode
        )
        
        self.coordinators = {
            "normal": self.normal_coordinator,
            "slow": self.slow_coordinator,
        }
    
    async def async_setup(self):
        """Set up all coordinators and start their polling."""
        _LOGGER.info("Setting up CoordinatorManager")
        
        # Initial data fetch for all coordinators
        for name, coordinator in self.coordinators.items():
            try:
                await coordinator.async_config_entry_first_refresh()
                _LOGGER.info(f"{name} coordinator first refresh completed")
            except Exception as e:
                _LOGGER.warning(f"{name} coordinator first refresh failed: {e}")
        
        # Create dummy entities to trigger automatic updates
        await self._create_dummy_entities()
        
        _LOGGER.info("CoordinatorManager setup completed")
    
    async def _create_dummy_entities(self):
        """Create dummy entities to ensure coordinators keep running."""
        # The DataUpdateCoordinator needs entities to be bound to start polling
        # We create a simple periodic task instead
        
        for name, coordinator in self.coordinators.items():
            # Create a periodic task for each coordinator
            self.hass.loop.create_task(self._periodic_refresh(coordinator, name))
            _LOGGER.debug(f"Created periodic refresh task for {name} coordinator")
    
    async def _periodic_refresh(self, coordinator, name):
        """Periodic refresh for coordinators."""
        import asyncio
        import random
        
        while True:
            try:
                # Add jitter to prevent synchronization
                base_interval = coordinator.update_interval.total_seconds()
                jitter_range = base_interval * 0.2  # 20% jitter
                jitter = random.uniform(-jitter_range, jitter_range)
                sleep_time = base_interval + jitter
                
                await asyncio.sleep(sleep_time)
                await coordinator._async_update_data()
                _LOGGER.debug(f"Periodic refresh completed for {name} coordinator (slept {sleep_time:.1f}s)")
            except Exception as e:
                _LOGGER.error(f"Error in periodic refresh for {name} coordinator: {e}")
                await asyncio.sleep(30)  # Wait 30 seconds on error
    
    async def async_shutdown(self):
        """Shutdown all coordinators."""
        _LOGGER.info("Shutting down CoordinatorManager")
        
        for name, coordinator in self.coordinators.items():
            try:
                if hasattr(coordinator, '_cancel_update'):
                    coordinator._cancel_update()
                _LOGGER.info(f"{name} coordinator shutdown completed")
            except Exception as e:
                _LOGGER.warning(f"{name} coordinator shutdown failed: {e}")
    
    def get_coordinator(self, coordinator_type: str):
        """Get a specific coordinator by type."""
        return self.coordinators.get(coordinator_type)
    
    def get_all_data(self):
        """Get combined data from all coordinators."""
        combined_data = {}
        for coordinator in self.coordinators.values():
            if hasattr(coordinator, 'data') and coordinator.data:
                combined_data.update(coordinator.data)
        return combined_data
