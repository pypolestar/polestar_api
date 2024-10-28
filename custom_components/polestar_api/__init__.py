"""Polestar EV integration."""

import logging

import httpx
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv

from .const import CONF_VIN, DOMAIN
from .polestar import PolestarCar, PolestarCoordinator
from .pypolestar.exception import PolestarApiException, PolestarAuthException

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
    coordinator = PolestarCoordinator(
        hass=hass,
        username=conf[CONF_USERNAME],
        password=conf[CONF_PASSWORD],
        vin=conf.get(CONF_VIN),
    )

    hass.data.setdefault(DOMAIN, {})

    try:
        await coordinator.async_init()

        entities: list[PolestarCar] = []
        for car in coordinator.get_cars():
            await car.async_update()
            entities.append(car)
            _LOGGER.debug("Added entity for VIN %s", car.vin)

        hass.data[DOMAIN][config_entry.entry_id] = entities
        await hass.config_entries.async_forward_entry_setups(
            config_entry, ["sensor", "image"]
        )
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
    coordinator.polestar_api.latest_call_code = 500
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
