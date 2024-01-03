"""Base class for Polestar entities."""
import logging

from homeassistant.helpers.entity import DeviceInfo, Entity

from .const import DOMAIN as POLESTAR_API_DOMAIN
from .polestar import Polestar

_LOGGER = logging.getLogger(__name__)


class PolestarEntity(Entity):
    """Base class for Polestar entities."""

    def __init__(self, device: Polestar) -> None:
        """Initialize the Polestar entity."""
        self._device = device

        self._attr_device_info = DeviceInfo(
            identifiers={(POLESTAR_API_DOMAIN, self._device.name)},
            manufacturer="Polestar",
            model=None,
            name=device.name,
            sw_version=None,
        )

    async def async_added_to_hass(self) -> None:
        """Add listener for state changes."""
        await super().async_added_to_hass()
