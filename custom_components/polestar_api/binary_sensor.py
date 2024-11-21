"""Support for Polestar binary sensors."""

import logging
from typing import Final

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN as POLESTAR_API_DOMAIN
from .data import PolestarConfigEntry
from .entity import PolestarEntity
from .polestar import PolestarCar

_LOGGER = logging.getLogger(__name__)


ENTITY_DESCRIPTIONS: Final[tuple[BinarySensorEntityDescription, ...]] = (
    BinarySensorEntityDescription(
        key="api_connected",
        name="API Connected",
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
            car=car,
            entity_description=entity_description,
        )
        for entity_description in ENTITY_DESCRIPTIONS
        for car in entry.runtime_data.cars
    )


class PolestarBinarySensor(PolestarEntity, BinarySensorEntity):
    """integration_blueprint binary_sensor class."""

    def __init__(
        self,
        car: PolestarCar,
        entity_description: BinarySensorEntityDescription,
    ) -> None:
        """Initialize the binary_sensor class."""
        super().__init__(car)
        self.car = car
        self.entity_description = entity_description
        self.entity_id = f"{POLESTAR_API_DOMAIN}.'polestar_'.{car.get_short_id()}_{entity_description.key}"
        self._attr_unique_id = (
            f"polestar_{car.get_unique_id()}_{entity_description.key}"
        )
        self._attr_translation_key = f"polestar_{entity_description.key}"

    @property
    def is_on(self) -> bool | None:
        """Return true if the binary_sensor is on."""
        return self.car.data.get(self.entity_description.key)
