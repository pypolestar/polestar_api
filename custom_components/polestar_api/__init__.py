"""Polestar EV integration."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import httpx
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.exceptions import (
    ConfigEntryAuthFailed,
    ConfigEntryError,
    ConfigEntryNotReady,
)
from homeassistant.helpers.device_registry import DeviceEntry
from homeassistant.loader import async_get_loaded_integration
from homeassistant.util.ssl import client_context
from pypolestar.exceptions import PolestarAuthException, PolestarAuthFailedException

from .const import CONF_VIN
from .coordinator import PolestarCoordinator
from .data import PolestarData
from .keycloak_auth import PolestarMfaRequiredException, create_polestar_api

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from .data import PolestarConfigEntry

PLATFORMS = [Platform.IMAGE, Platform.SENSOR, Platform.BINARY_SENSOR]

_LOGGER = logging.getLogger(__name__)


def _create_client_session() -> httpx.AsyncClient:
    """Create the HTTP client owned by a config entry."""
    # Home Assistant caches this SSL context, so a setup retry does not load
    # the CA bundle on the event loop again.
    return httpx.AsyncClient(verify=client_context())


async def _async_close_connection(api_client, client_session) -> None:
    """Close the gRPC channels and the HTTP client of a Polestar API client."""
    try:
        await api_client.async_logout()
    except Exception:
        # Cleanup must not hide the original setup or unload result.
        _LOGGER.debug("Polestar logout failed during cleanup", exc_info=True)
    await client_session.aclose()


async def async_setup_entry(hass: HomeAssistant, entry: PolestarConfigEntry) -> bool:
    """Set up Polestar from a config entry."""

    _LOGGER.debug("async_setup_entry: %s", entry)

    vin = entry.data.get(CONF_VIN)

    # The integration owns the client lifetime: Home Assistant calls
    # async_unload_entry only after a successful setup, and setup can retry.
    # A client from create_async_httpx_client cannot be closed by the
    # integration, because Home Assistant replaces aclose with a report-only
    # stub.
    client_session = _create_client_session()

    api_client = create_polestar_api(
        username=entry.data[CONF_USERNAME],
        password=entry.data[CONF_PASSWORD],
        client_session=client_session,
        vins=[vin] if vin else None,
        unique_id=entry.entry_id,
        enable_grpc=True,
    )

    loaded = False
    try:
        await api_client.async_init()

        available_vins = api_client.get_available_vins()

        if not available_vins:
            raise ConfigEntryError("No cars found for the provided credentials")

        coordinators = []

        for coordinator in [
            PolestarCoordinator(
                hass=hass,
                api=api_client,
                config_entry=entry,
                vin=vin,
            )
            for vin in available_vins
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

        loaded = True
    except PolestarMfaRequiredException as exc:
        # ConfigEntryAuthFailed starts the reauth flow, where the user can
        # enter the current credentials after signing in at polestar.com.
        raise ConfigEntryAuthFailed(str(exc)) from exc
    except PolestarAuthFailedException as exc:
        raise ConfigEntryAuthFailed from exc
    except PolestarAuthException as exc:
        # A temporary failure of the Polestar ID service. Retry, do not ask
        # the user for a password.
        raise ConfigEntryNotReady(str(exc)) from exc
    except httpx.HTTPError as exc:
        raise ConfigEntryNotReady(str(exc)) from exc
    finally:
        if not loaded:
            await _async_close_connection(api_client, client_session)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: PolestarConfigEntry) -> bool:
    """Handle removal of an entry."""

    _LOGGER.debug("async_unload_entry: %s", entry)

    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unloaded and (runtime_data := getattr(entry, "runtime_data", None)):
        await _async_close_connection(
            runtime_data.api_client, runtime_data.api_client.client_session
        )

    return unloaded


async def async_remove_config_entry_device(
    hass: HomeAssistant, config_entry: PolestarConfigEntry, device_entry: DeviceEntry
) -> bool:
    """Remove a config entry from a device."""
    return True
