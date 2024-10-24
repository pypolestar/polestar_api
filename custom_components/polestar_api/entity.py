"""Base class for Polestar entities."""

import logging

from homeassistant.helpers.entity import Entity

from .polestar import Polestar

_LOGGER = logging.getLogger(__name__)


class PolestarEntity(Entity):
    """Base class for Polestar entities."""

    def __init__(self, device: Polestar) -> None:
        """Initialize the Polestar entity."""
        self.device = device
        self._attr_device_info = device.get_device_info()

    def get_device(self):
        """Return the device."""
        return self.device

    async def async_added_to_hass(self) -> None:
        """Add listener for state changes."""
        await super().async_added_to_hass()
