"""Polestar EV integration."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.helpers.httpx_client import create_async_httpx_client
from homeassistant.loader import async_get_loaded_integration
from pypolestar import PolestarApi

from .const import CONF_VIN
from .coordinator import PolestarCoordinator
from .data import PolestarData

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from .data import PolestarConfigEntry

PLATFORMS = [Platform.IMAGE, Platform.SENSOR, Platform.BINARY_SENSOR]

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: PolestarConfigEntry) -> bool:
    """Set up Polestar from a config entry."""

    _LOGGER.debug("async_setup_entry: %s", entry)

    vin = entry.data.get(CONF_VIN)

    api_client = PolestarApi(
        username=entry.data[CONF_USERNAME],
        password=entry.data[CONF_PASSWORD],
        client_session=create_async_httpx_client(hass),
        vins=[vin] if vin else None,
        unique_id=entry.entry_id,
    )

    await api_client.async_init()

    coordinators = []

    for coordinator in [
        PolestarCoordinator(
            hass=hass,
            api=api_client,
            config_entry=entry,
            vin=vin,
        )
        for vin in api_client.get_available_vins()
    ]:
        await coordinator.async_config_entry_first_refresh()
        coordinators.append(coordinator)
        _LOGGER.debug(
            "Added car with VIN %s for %s",
            coordinator.vin,
            entry.entry_id,
        )

    entry.runtime_data = PolestarData(
        api_client=api_client,
        coordinators=coordinators,
        integration=async_get_loaded_integration(hass, entry.domain),
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    return True


async def async_reload_entry(hass: HomeAssistant, entry: PolestarConfigEntry) -> None:
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)


async def async_unload_entry(hass: HomeAssistant, entry: PolestarConfigEntry) -> bool:
    """Handle removal of an entry."""

    _LOGGER.debug("async_unload_entry: %s", entry)
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
