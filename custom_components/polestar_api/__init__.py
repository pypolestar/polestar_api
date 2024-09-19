"""Polestar EV integration."""

import asyncio
from asyncio import timeout
import logging

from aiohttp import ClientConnectionError
import httpx

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import config_validation as cv

from .const import DOMAIN, TIMEOUT
from .polestar import Polestar
from .pypolestar.exception import PolestarApiException, PolestarAuthException
from .pypolestar.polestar import PolestarApi

PLATFORMS = [Platform.IMAGE, Platform.SENSOR]

CONFIG_SCHEMA = cv.removed(DOMAIN, raise_if_present=False)

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the Polestar API component."""
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Set up Polestar from a config entry."""
    conf = config_entry.data

    _LOGGER.debug("async_setup_entry: %s", config_entry)
    polestar = Polestar(hass, conf[CONF_USERNAME], conf[CONF_PASSWORD])

    try:
        await polestar.init()
        number_of_cars = polestar.get_number_of_cars()
        hass.data.setdefault(DOMAIN, {})

        # for each number of car we are going to create a new entry
        entities = []
        for index in range(number_of_cars):
            polestar = Polestar(hass, conf[CONF_USERNAME], conf[CONF_PASSWORD])
            await polestar.init()
            polestar.set_car_data(index)
            polestar.set_vin()
            polestar.set_config_unit(hass.config.units)
            entities.append(polestar)

        hass.data[DOMAIN][config_entry.entry_id] = entities

        await hass.config_entries.async_forward_entry_setup(config_entry, "sensor")
        return True
    except PolestarApiException as e:
        _LOGGER.exception("API Exception on update data %s", str(e))
    except PolestarAuthException as e:
        _LOGGER.exception("Auth Exception on update data %s", str(e))
    except httpx.ConnectTimeout as e:
        _LOGGER.exception("Connection Timeout on update data %s", str(e))
    except httpx.ConnectError as e:
        _LOGGER.exception("Connection Error on update data %s", str(e))
    except httpx.ReadTimeout as e:
        _LOGGER.exception("Read Timeout on update data %s", str(e))
    except Exception as e:
        _LOGGER.exception("Unexpected Error on update data %s", str(e))
    polestar.polestarApi.latest_call_code = 500
    return False


async def async_unload_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.debug("async_unload_entry: %s", config_entry)

    unload_ok = await hass.config_entries.async_unload_platforms(
        config_entry, PLATFORMS
    )

    hass.data[DOMAIN].pop(config_entry.entry_id)

    if not hass.data[DOMAIN]:
        hass.data.pop(DOMAIN)

    return unload_ok


async def polestar_setup(
    hass: HomeAssistant, name: str, username: str, password: str
) -> PolestarApi | None:
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
