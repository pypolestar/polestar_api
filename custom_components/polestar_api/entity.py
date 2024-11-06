"""Base class for Polestar entities."""

import logging

from homeassistant.helpers.entity import Entity

from .polestar import PolestarCar

_LOGGER = logging.getLogger(__name__)


class PolestarEntity(Entity):
    """Base class for Polestar entities."""

    def __init__(self, car: PolestarCar) -> None:
        """Initialize the Polestar entity."""
        self._attr_device_info = car.get_device_info()

    async def async_added_to_hass(self) -> None:
        """Add listener for state changes."""
        await super().async_added_to_hass()
