"""Config flow for the Polestar EV platform."""

import logging

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.helpers.httpx_client import get_async_client

from .const import CONF_VIN, DOMAIN
from .pypolestar.exception import PolestarApiException, PolestarAuthException
from .pypolestar.polestar import PolestarApi

_LOGGER = logging.getLogger(__name__)


class NoCarsFoundException(Exception):
    pass


class VinNotFoundException(Exception):
    pass


@config_entries.HANDLERS.register(DOMAIN)
class FlowHandler(config_entries.ConfigFlow):
    """Handle a config flow."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL

    async def async_step_user(self, user_input: dict | None = None) -> ConfigFlowResult:
        """User initiated config flow."""
        _errors = {}

        if user_input is not None:
            username = user_input[CONF_USERNAME]
            password = user_input[CONF_PASSWORD]
            vin = user_input.get(CONF_VIN)

            try:
                await self._test_credentials(username, password, vin)
            except NoCarsFoundException as exc:
                _LOGGER.error(exc)
                _errors["base"] = "no_cars_found"
            except VinNotFoundException as exc:
                _LOGGER.error(exc)
                _errors["base"] = "vin_not_found"
            except PolestarAuthException as exc:
                _LOGGER.warning(exc)
                _errors["base"] = "auth_failed"
            except PolestarApiException as exc:
                _LOGGER.error(exc)
                _errors["base"] = "api"
            else:
                return self.async_create_entry(
                    title=f"Polestar EV for {username}",
                    data={
                        CONF_USERNAME: username,
                        CONF_PASSWORD: password,
                        CONF_VIN: vin,
                    },
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_USERNAME): str,
                    vol.Required(CONF_PASSWORD): str,
                    vol.Optional(CONF_VIN): str,
                }
            ),
            errors=_errors,
        )

    async def _test_credentials(
        self, username: str, password: str, vin: str | None
    ) -> None:
        """Validate credentials and return VINs of found cars."""

        api_client = PolestarApi(
            username=username,
            password=password,
            client_session=get_async_client(self.hass),
        )

        try:
            await api_client.async_init()

            if found_vins := api_client.get_available_vins():
                _LOGGER.debug("Found %d VINs for %s", len(found_vins), username)
            else:
                _LOGGER.warning("No VINs found for %s", username)
                raise NoCarsFoundException

            if vin and vin not in found_vins:
                _LOGGER.warning("VIN %s not found for %s", vin, username)
                raise VinNotFoundException
        finally:
            await api_client.async_logout()
