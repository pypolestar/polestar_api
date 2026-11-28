"""Config flow for the Polestar EV platform."""

import logging
from collections.abc import Mapping
from typing import Any

import httpx
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from pypolestar.exceptions import PolestarApiException, PolestarAuthFailedException

from .const import CONF_VIN, DOMAIN
from .keycloak_auth import PolestarMfaRequiredException, create_polestar_api

_LOGGER = logging.getLogger(__name__)


class NoCarsFoundException(Exception):
    pass


class VinNotFoundException(Exception):
    pass


@config_entries.HANDLERS.register(DOMAIN)
class FlowHandler(config_entries.ConfigFlow):
    """Handle a config flow."""

    VERSION = 1

    async def async_step_user(self, user_input: dict | None = None) -> ConfigFlowResult:
        """User initiated config flow."""
        errors = {}

        if user_input is not None:
            username = user_input[CONF_USERNAME]
            password = user_input[CONF_PASSWORD]
            vin = user_input.get(CONF_VIN)

            errors = await self._async_validate_credentials(username, password, vin)

            if not errors:
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
            errors=errors,
        )

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Start reauthentication after an authentication error."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict | None = None
    ) -> ConfigFlowResult:
        """Ask for the password of the reauthenticated account."""
        reauth_entry = self._get_reauth_entry()
        # Reauthentication must keep the account of the entry. Do not accept a
        # different username here, or the entry would change owner.
        username = reauth_entry.data[CONF_USERNAME]
        errors = {}

        if user_input is not None:
            password = user_input[CONF_PASSWORD]
            errors = await self._async_validate_credentials(
                username, password, reauth_entry.data.get(CONF_VIN)
            )

            if not errors:
                return self.async_update_reload_and_abort(
                    reauth_entry,
                    data_updates={CONF_PASSWORD: password},
                )

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema({vol.Required(CONF_PASSWORD): str}),
            errors=errors,
            description_placeholders={"username": username},
        )

    async def _async_validate_credentials(
        self, username: str, password: str, vin: str | None
    ) -> dict[str, str]:
        """Validate credentials and return config flow errors, if any."""
        try:
            await self._test_credentials(username, password, vin)
        except NoCarsFoundException as exc:
            _LOGGER.error(exc)
            return {"base": "no_cars_found"}
        except VinNotFoundException as exc:
            _LOGGER.error(exc)
            return {"base": "vin_not_found"}
        except PolestarMfaRequiredException as exc:
            _LOGGER.warning(exc)
            return {"base": "mfa_required"}
        except PolestarAuthFailedException as exc:
            _LOGGER.warning(exc)
            return {"base": "auth_failed"}
        except PolestarApiException as exc:
            # Includes PolestarAuthException, for example an unavailable
            # Polestar ID service. Do not report this as a wrong password.
            _LOGGER.error(exc)
            return {"base": "api"}
        except httpx.HTTPError as exc:
            # pypolestar does not wrap every transport error.
            _LOGGER.error("Connection to Polestar failed: %s", exc)
            return {"base": "api"}
        return {}

    async def _test_credentials(
        self, username: str, password: str, vin: str | None
    ) -> None:
        """Validate credentials and return VINs of found cars."""

        # Use a dedicated client for each validation. The shared Home Assistant
        # client can keep the Keycloak session of a previous account, and that
        # session must not validate a different account.
        async with httpx.AsyncClient() as client_session:
            api_client = create_polestar_api(
                username=username,
                password=password,
                client_session=client_session,
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
