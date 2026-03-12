"""Runtime data class for Daikin Altherma Modbus integration."""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .coordinator_manager import CoordinatorManager, UnifiedCoordinator


@dataclass
class RuntimeData:
    """Runtime data for the Daikin Altherma Modbus integration."""

    coordinator: "UnifiedCoordinator"
    normal_coordinator: Any
    slow_coordinator: Any
    manager: "CoordinatorManager"

    def get_coordinator(self, coordinator_type: str):
        """Get a specific coordinator by type."""
        return self.manager.get_coordinator(coordinator_type)

    def get_all_data(self):
        """Get combined data from all coordinators."""
        return self.manager.get_all_data()
