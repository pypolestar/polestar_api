"""Support Polestar image."""
from __future__ import annotations

from dataclasses import dataclass
import datetime
import logging
from typing import Final

from homeassistant.components.image import Image, ImageEntity, ImageEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_platform
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import DOMAIN as POLESTAR_API_DOMAIN
from .entity import PolestarEntity
from .polestar import Polestar

_LOGGER = logging.getLogger(__name__)

@dataclass
class PolestarImageDescriptionMixin:
    """A mixin class for image entities."""

    query: str
    field_name: str

@dataclass
class PolestarImageDescription(
    ImageEntityDescription,  PolestarImageDescriptionMixin
):
    """A class that describes image entities."""


POLESTAR_IMAGE_TYPES: Final[tuple[PolestarImageDescription, ...]] = (
    PolestarImageDescription(
        query="getConsumerCarsV2",
        field_name="content/images/studio/url",
        key="car_image",
        entity_registry_enabled_default=False,
    ),
)

async def async_setup_entry(
        hass: HomeAssistant,
        entry: ConfigEntry,
        async_add_entities: AddEntitiesCallback) -> None:
    """Set up Polestar image entities based on a config entry."""
     # get the device
    device: Polestar
    device = hass.data[POLESTAR_API_DOMAIN][entry.entry_id]
    await device.init()

    # put data in cache
    await device.async_update()

    images = [
        PolestarImage(device, description, hass) for description in POLESTAR_IMAGE_TYPES
    ]
    async_add_entities(images)
    entity_platform.current_platform.get()

class PolestarImage(PolestarEntity, ImageEntity):
    """Representation of a Polestar image."""

    entity_description: PolestarImageDescription

    def __init__(
        self,
        device: Polestar,
        description: PolestarImageDescription,
        hass: HomeAssistant,
    ) -> None:
        """Initialize the Polestar image."""
        super().__init__(device)
        ImageEntity.__init__(self, hass)
        self._device = device
        # get the last 4 character of the id
        unique_id = device.vin[-4:]
        self.entity_id = f"{POLESTAR_API_DOMAIN}.'polestar_'.{unique_id}_{description.key}"
        self._attr_unique_id = f"polestar_{unique_id}-{description.key}"
        self.entity_description = description
        self._attr_translation_key = f"polestar_{description.key}"
        self._attr_image_last_updated = datetime.datetime.now()


    @property
    def image_url(self) -> str | None:
        """Return the image URL."""
        return self._device.get_value(self.entity_description.query, self.entity_description.field_name)

    async def async_load_image(self) -> Image | None:
        """Load an image."""
        if self.image_url is None:
            return None

        await self._device.async_update()
        value = self._device.get_value(
            self.entity_description.query, self.entity_description.field_name, True)

        return Image(
            content=value,
            content_type="image/png",
        )
