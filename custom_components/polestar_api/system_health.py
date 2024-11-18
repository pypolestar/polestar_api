"""Provide info to system health."""

from homeassistant.components import system_health
from homeassistant.core import HomeAssistant, callback

from .pypolestar.const import API_AUTH_URL, API_MYSTAR_V2_URL


@callback
def async_register(
    hass: HomeAssistant, register: system_health.SystemHealthRegistration
) -> None:
    """Register system health callbacks."""
    register.async_register_info(system_health_info)


async def system_health_info(hass):
    """Get info for the info page."""
    return {
        "Auth API": system_health.async_check_can_reach_url(hass, API_AUTH_URL),
        "Data API": system_health.async_check_can_reach_url(hass, API_MYSTAR_V2_URL),
    }
