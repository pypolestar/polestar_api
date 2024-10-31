"""Polestar EV integration."""

import logging

import httpx
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant
from homeassistant.loader import async_get_loaded_integration

from .const import CONF_VIN
from .data import PolestarConfigEntry, PolestarData
from .polestar import PolestarCar, PolestarCoordinator
from .pypolestar.exception import PolestarApiException, PolestarAuthException

PLATFORMS = [Platform.IMAGE, Platform.SENSOR]

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: PolestarConfigEntry) -> bool:
    """Set up Polestar from a config entry."""

    _LOGGER.debug("async_setup_entry: %s", entry)

    coordinator = PolestarCoordinator(
        hass=hass,
        username=entry.data[CONF_USERNAME],
        password=entry.data[CONF_PASSWORD],
        vin=entry.data.get(CONF_VIN),
    )

    try:
        await coordinator.async_init()

        cars: list[PolestarCar] = []
        for car in coordinator.get_cars():
            await car.async_update()
            cars.append(car)
            _LOGGER.debug("Added car with VIN %s", car.vin)

        entry.runtime_data = PolestarData(
            coordinator=coordinator,
            cars=cars,
            integration=async_get_loaded_integration(hass, entry.domain),
        )

        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
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


async def async_unload_entry(hass: HomeAssistant, entry: PolestarConfigEntry) -> bool:
    """Handle removal of an entry."""

    _LOGGER.debug("async_unload_entry: %s", entry)
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
