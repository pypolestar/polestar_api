"""Polestar EV integration."""

import asyncio
import logging

from aiohttp import ClientConnectionError
from async_timeout import timeout

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import config_validation as cv

from .const import DOMAIN, TIMEOUT
from .polestar import Polestar
from .pypolestar.exception import PolestarApiException
from .pypolestar.polestar import PolestarApi

PLATFORMS = [
    Platform.SENSOR,
]

CONFIG_SCHEMA = cv.removed(DOMAIN, raise_if_present=False)

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the Polestar API component."""
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    conf = config_entry.data

    _LOGGER.debug("async_setup_entry: %s", config_entry)
    polestarApi = Polestar(
        hass, conf[CONF_USERNAME], conf[CONF_PASSWORD])
    try:
        await polestarApi.init()

        hass.data.setdefault(DOMAIN, {})
        hass.data[DOMAIN][config_entry.entry_id] = polestarApi

        await hass.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)

        return True
    except PolestarApiException as e:
        _LOGGER.exception("API Exception %s", str(e))


async def async_unload_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.debug("async_unload_entry: %s", config_entry)

    unload_ok = await hass.config_entries.async_unload_platforms(config_entry, PLATFORMS)

    hass.data[DOMAIN].pop(config_entry.entry_id)

    if not hass.data[DOMAIN]:
        hass.data.pop(DOMAIN)

    return unload_ok


async def polestar_setup(hass: HomeAssistant, name: str, username: str, password: str) -> PolestarApi | None:
    """Create a Polestar instance only once."""

    try:
        with timeout(TIMEOUT):
            device = Polestar(hass, name, username, password)
            await device.init()
    except asyncio.TimeoutError:
        _LOGGER.debug("Connection to %s timed out", name)
        raise ConfigEntryNotReady
    except ClientConnectionError as e:
        _LOGGER.debug("ClientConnectionError to %s %s", name, str(e))
        raise ConfigEntryNotReady
    except Exception as e:  # pylint: disable=broad-except
        _LOGGER.error("Unexpected error creating device %s %s", name, str(e))
        return None

    return device
