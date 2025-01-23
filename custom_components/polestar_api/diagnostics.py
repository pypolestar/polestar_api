"""Provides diagnostics for Polestar API."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.const import CONF_PASSWORD

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from .data import PolestarConfigEntry


TO_REDACT = {CONF_PASSWORD}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: PolestarConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""

    cars = entry.runtime_data.coordinators
    api = entry.runtime_data.api_client

    return {
        "config_entry_data": async_redact_data(dict(entry.data), TO_REDACT),
        "cars": [{"vin": car.vin, "name": car.name, "data": car.data} for car in cars],
        "auth_api": {
            "oidc_provider": api.auth.oidc_provider,
            "access_token_valid": api.auth.is_token_valid(),
            "status": api.auth.get_status_code(),
        },
        "data_api": {
            "endpoint": api.api_url,
            "status": api.get_status_code(),
        },
    }
