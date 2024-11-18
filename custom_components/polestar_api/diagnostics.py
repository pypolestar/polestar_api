"""Provides diagnostics for Polestar API."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.const import CONF_PASSWORD
from homeassistant.core import HomeAssistant

from .data import PolestarConfigEntry

TO_REDACT = {CONF_PASSWORD}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: PolestarConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""

    coordinator = entry.runtime_data.coordinator
    cars = entry.runtime_data.cars
    api = coordinator.polestar_api

    return {
        "config_entry_data": async_redact_data(dict(entry.data), TO_REDACT),
        "cars": [{"vin": car.vin, "model": car.model} for car in cars],
        "auth_api": {
            "oidc_provider": api.auth.oidc_provider,
            "access_token_valid": api.auth.is_token_valid(),
            "endpoint": api.auth.api_url,
            "status": api.auth.latest_call_code,
        },
        "data_api": {"endpoint": api.api_url, "status": api.latest_call_code},
    }
