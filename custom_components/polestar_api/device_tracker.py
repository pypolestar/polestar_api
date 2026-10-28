"""Support for the Polestar last parked location."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from homeassistant.components.device_tracker import SourceType, TrackerEntity

from .entity import PolestarEntity, PolestarEntityDataSource, PolestarEntityDescription

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .data import PolestarConfigEntry

_LOGGER = logging.getLogger(__name__)

LOCATION_DESCRIPTION = PolestarEntityDescription(
    key="location",
    icon="mdi:car-connected",
    data_source=PolestarEntityDataSource.GRPC_LOCATION,
    data_state_attribute="latitude",
    data_extra_state_attributes={
        "parked_at": "timestamp",
        "stale": "stale",
    },
)


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001 Unused function argument: `hass`
    entry: PolestarConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the device_tracker platform."""
    async_add_entities(
        PolestarDeviceTracker(
            coordinator=coordinator,
            entity_description=LOCATION_DESCRIPTION,
        )
        for coordinator in entry.runtime_data.coordinators
    )


class PolestarDeviceTracker(PolestarEntity, TrackerEntity):
    """Last parked location of the car (gRPC GetLastParkedLocation)."""

    _attr_has_entity_name = True

    @property
    def source_type(self) -> SourceType:
        """Return the source type of the device."""
        return SourceType.GPS

    @property
    def latitude(self) -> float | None:
        """Return latitude of the last parked location."""
        data = self.coordinator.grpc_location_data
        return data.latitude if data else None

    @property
    def longitude(self) -> float | None:
        """Return longitude of the last parked location."""
        data = self.coordinator.grpc_location_data
        return data.longitude if data else None

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return when the car was parked and the backend's freshness flag."""
        return self.get_extra_state_attributes()
