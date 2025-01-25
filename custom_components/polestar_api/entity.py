"""Base class for Polestar entities."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import ATTRIBUTION, DOMAIN
from .coordinator import PolestarCoordinator

if TYPE_CHECKING:
    from homeassistant.helpers.entity import EntityDescription


class PolestarEntity(CoordinatorEntity[PolestarCoordinator]):
    """Base class for Polestar entities."""

    _attr_attribution = ATTRIBUTION

    def __init__(
        self, coordinator: PolestarCoordinator, entity_description: EntityDescription
    ) -> None:
        """Initialize the Polestar entity."""
        super().__init__(coordinator)
        self.entity_description = entity_description
        self.entity_id = (
            f"{DOMAIN}.polestar_{coordinator.get_short_id()}_{entity_description.key}"
        )
        self._attr_unique_id = (
            f"polestar_{coordinator.unique_id}_{entity_description.key}"
        )
        self._attr_translation_key = f"polestar_{entity_description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self.coordinator.unique_id)},
            manufacturer="Polestar",
            model=self.coordinator.model,
            name=self.coordinator.name,
            serial_number=self.coordinator.vin,
        )
