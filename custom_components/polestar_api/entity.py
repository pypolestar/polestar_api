"""Base class for Polestar entities."""

import logging

from homeassistant.helpers.entity import DeviceInfo, Entity

from .const import DOMAIN as POLESTAR_API_DOMAIN
from .polestar import Polestar

_LOGGER = logging.getLogger(__name__)


class PolestarEntity(Entity):
    """Base class for Polestar entities."""

    def init(self):
        """Initialize the Polestar entity."""
        self.device = None

    def __init__(self) -> None:
        """Initialize the Polestar entity."""
        self.device = None

    def set_device(self, device: Polestar):
        """Set the device."""
        self.device = device

        self._attr_device_info = DeviceInfo(
            identifiers={(POLESTAR_API_DOMAIN, self.device.name)},
            manufacturer="Polestar",
            model=None,
            name=device.name,
            sw_version=None,
        )

    def get_device(self):
        """Return the device."""
        return self.device

    async def async_added_to_hass(self) -> None:
        """Add listener for state changes."""
        await super().async_added_to_hass()
