"""Support for Polestar binary sensors."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Final

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.const import EntityCategory

from .entity import PolestarEntity

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .coordinator import PolestarCoordinator
    from .data import PolestarConfigEntry

_LOGGER = logging.getLogger(__name__)


ENTITY_DESCRIPTIONS: Final[tuple[BinarySensorEntityDescription, ...]] = (
    BinarySensorEntityDescription(
        key="api_connected",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001 Unused function argument: `hass`
    entry: PolestarConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the binary_sensor platform."""
    async_add_entities(
        PolestarBinarySensor(
            coordinator=coordinator,
            entity_description=entity_description,
        )
        for coordinator in entry.runtime_data.coordinators
        for entity_description in ENTITY_DESCRIPTIONS
    )


class PolestarBinarySensor(PolestarEntity, BinarySensorEntity):
    """integration_blueprint binary_sensor class."""

    entity_description: BinarySensorEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: PolestarCoordinator,
        entity_description: BinarySensorEntityDescription,
    ) -> None:
        """Initialize the binary_sensor class."""
        super().__init__(coordinator, entity_description)

    @property
    def is_on(self) -> bool | None:
        """Return true if the binary_sensor is on."""
        return self.coordinator.data.get(self.entity_description.key)
