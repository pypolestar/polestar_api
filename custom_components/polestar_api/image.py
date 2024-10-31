"""Support Polestar image."""

from __future__ import annotations

import datetime
import logging
from dataclasses import dataclass
from functools import cached_property
from typing import Final

from homeassistant.components.image import ImageEntity, ImageEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN as POLESTAR_API_DOMAIN
from .data import PolestarConfigEntry
from .entity import PolestarEntity
from .polestar import PolestarCar

_LOGGER = logging.getLogger(__name__)


@dataclass
class PolestarImageDescriptionMixin:
    """A mixin class for image entities."""

    query: str
    field_name: str


@dataclass
class PolestarImageDescription(ImageEntityDescription, PolestarImageDescriptionMixin):
    """A class that describes image entities."""


POLESTAR_IMAGE_TYPES: Final[tuple[PolestarImageDescription, ...]] = (
    PolestarImageDescription(
        key="car_image",
        name="Car Image",
        query="getConsumerCarsV2",
        field_name="content/images/studio/url",
        entity_registry_enabled_default=False,
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
            PolestarImage(car, entity_description, hass)
            for entity_description in POLESTAR_IMAGE_TYPES
            for car in entry.runtime_data.cars
        ]
    )


class PolestarImage(PolestarEntity, ImageEntity):
    """Representation of a Polestar image."""

    entity_description: PolestarImageDescription

    def __init__(
        self,
        car: PolestarCar,
        entity_description: PolestarImageDescription,
        hass: HomeAssistant,
    ) -> None:
        """Initialize the Polestar image."""
        super().__init__(car)
        ImageEntity.__init__(self, hass)
        self.car = car
        self.entity_description = entity_description
        self.entity_id = f"{POLESTAR_API_DOMAIN}.'polestar_'.{car.get_short_id()}_{entity_description.key}"
        self._attr_unique_id = (
            f"polestar_{car.get_unique_id()}_{entity_description.key}"
        )
        self._attr_translation_key = f"polestar_{entity_description.key}"
        self._attr_image_last_updated = datetime.datetime.now()

    @cached_property
    def image_url(self) -> str | None:
        """Return the image URL."""
        return self.car.get_value(
            self.entity_description.query, self.entity_description.field_name
        )
