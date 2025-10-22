"""Support Polestar image."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

import homeassistant.util.dt as dt_util
from homeassistant.components.image import ImageEntity, ImageEntityDescription

from .entity import PolestarEntity, PolestarEntityDataSource, PolestarEntityDescription

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .coordinator import PolestarCoordinator
    from .data import PolestarConfigEntry

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class PolestarImageDescription(ImageEntityDescription, PolestarEntityDescription):
    """Class to describe an Polestar image entity."""


ENTITY_DESCRIPTIONS: Final[tuple[PolestarImageDescription, ...]] = (
    PolestarImageDescription(
        key="car_image",
        entity_registry_enabled_default=False,
        data_source=PolestarEntityDataSource.INFORMATION,
        data_state_attribute="image_url",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PolestarConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Polestar image entities based on a config entry."""

    async_add_entities(
        [
            PolestarImage(coordinator, entity_description, hass)
            for coordinator in entry.runtime_data.coordinators
            for entity_description in ENTITY_DESCRIPTIONS
        ]
    )


class PolestarImage(PolestarEntity, ImageEntity):
    """Representation of a Polestar image."""

    entity_description: PolestarImageDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: PolestarCoordinator,
        entity_description: PolestarImageDescription,
        hass: HomeAssistant,
    ) -> None:
        """Initialize the Polestar image."""
        super().__init__(coordinator, entity_description)
        ImageEntity.__init__(self, hass)

    async def async_update_image_url(self) -> None:
        value = self.get_native_value()
        if value is None:
            _LOGGER.debug("No image URL found")
            self._attr_image_url = None
            self._attr_image_last_updated = dt_util.utcnow()
        elif isinstance(value, str) and value != self._attr_image_url:
            _LOGGER.debug("Returning updated image URL %s", value)
            self._attr_image_url = value
            self._attr_image_last_updated = dt_util.utcnow()

    async def async_image(self) -> bytes | None:
        """Return bytes of image."""
        await self.async_update_image_url()
        return await ImageEntity.async_image(self)
