"""Tests for config entry setup error handling."""

from __future__ import annotations

import asyncio
import sys
import types
from types import SimpleNamespace

import httpx
import pytest


def _install_homeassistant_stubs() -> None:
    """Install small Home Assistant stubs when Home Assistant is not installed."""
    try:
        import homeassistant  # noqa: F401
    except ModuleNotFoundError:
        pass
    else:
        return

    def module(name: str) -> types.ModuleType:
        mod = types.ModuleType(name)
        mod.__path__ = []
        sys.modules[name] = mod
        return mod

    try:
        import voluptuous  # noqa: F401
    except ModuleNotFoundError:
        vol = module("voluptuous")
        vol.Schema = lambda *args, **kwargs: None
        vol.Required = lambda *args, **kwargs: None
        vol.Optional = lambda *args, **kwargs: None

    ha = module("homeassistant")
    helpers = module("homeassistant.helpers")
    util = module("homeassistant.util")

    const = module("homeassistant.const")
    const.CONF_PASSWORD = "password"
    const.CONF_USERNAME = "username"

    class Platform:
        IMAGE = "image"
        SENSOR = "sensor"
        BINARY_SENSOR = "binary_sensor"

    const.Platform = Platform

    exceptions = module("homeassistant.exceptions")

    class HomeAssistantError(Exception):
        pass

    class ConfigEntryError(HomeAssistantError):
        pass

    class ConfigEntryAuthFailed(HomeAssistantError):
        pass

    exceptions.HomeAssistantError = HomeAssistantError
    exceptions.ConfigEntryError = ConfigEntryError
    exceptions.ConfigEntryAuthFailed = ConfigEntryAuthFailed

    config_entries = module("homeassistant.config_entries")

    class ConfigFlow:
        hass = None

        def async_show_form(self, **kwargs):
            return {"type": "form", **kwargs}

        def async_create_entry(self, **kwargs):
            return {"type": "create_entry", **kwargs}

    class ConfigFlowResult:
        pass

    class Handlers:
        @staticmethod
        def register(domain):
            return lambda cls: cls

    config_entries.ConfigFlow = ConfigFlow
    config_entries.ConfigFlowResult = ConfigFlowResult
    config_entries.HANDLERS = Handlers()
    config_entries.CONN_CLASS_LOCAL_POLL = "local_poll"

    device_registry = module("homeassistant.helpers.device_registry")
    device_registry.DeviceEntry = object

    httpx_client = module("homeassistant.helpers.httpx_client")
    httpx_client.create_async_httpx_client = lambda hass: None

    loader = module("homeassistant.loader")
    loader.async_get_loaded_integration = lambda hass, domain: None

    update_coordinator = module("homeassistant.helpers.update_coordinator")

    class DataUpdateCoordinator:
        pass

    class UpdateFailed(Exception):
        pass

    update_coordinator.DataUpdateCoordinator = DataUpdateCoordinator
    update_coordinator.UpdateFailed = UpdateFailed

    dt = module("homeassistant.util.dt")
    dt.as_local = lambda value: value

    ha.const = const
    ha.config_entries = config_entries
    ha.exceptions = exceptions
    ha.loader = loader
    helpers.device_registry = device_registry
    helpers.httpx_client = httpx_client
    helpers.update_coordinator = update_coordinator
    util.dt = dt


def _load_integration():
    """Import the integration once the Home Assistant stubs are ready."""
    _install_homeassistant_stubs()

    from homeassistant.exceptions import ConfigEntryError
    from pypolestar.exceptions import PolestarAuthFailedException

    import custom_components.polestar_api as integration
    from custom_components.polestar_api.keycloak_auth import (
        PolestarMfaRequiredException,
    )

    return (
        integration,
        ConfigEntryError,
        PolestarMfaRequiredException,
        PolestarAuthFailedException,
    )


def _load_config_flow():
    """Import the config flow once the Home Assistant stubs are ready."""
    _install_homeassistant_stubs()

    import custom_components.polestar_api.config_flow as config_flow

    return config_flow


def _make_entry() -> SimpleNamespace:
    return SimpleNamespace(
        data={"username": "user", "password": "pass", "vin": "VIN123"},
        entry_id="entry-1",
    )


def test_mfa_message_is_preserved_in_setup_error(monkeypatch):
    integration, ConfigEntryError, mfa_error, _ = _load_integration()

    class FakeApi:
        async def async_init(self) -> None:
            raise mfa_error("Sign in once at polestar.com")

    monkeypatch.setattr(integration, "create_polestar_api", lambda **kwargs: FakeApi())
    monkeypatch.setattr(integration, "create_async_httpx_client", lambda hass: None)

    with pytest.raises(ConfigEntryError) as exc_info:
        asyncio.run(integration.async_setup_entry(SimpleNamespace(), _make_entry()))

    assert str(exc_info.value) == "Sign in once at polestar.com"


def test_other_auth_errors_keep_empty_setup_error(monkeypatch):
    integration, ConfigEntryError, _, auth_failed = _load_integration()

    class FakeApi:
        async def async_init(self) -> None:
            raise auth_failed("bad password")

    monkeypatch.setattr(integration, "create_polestar_api", lambda **kwargs: FakeApi())
    monkeypatch.setattr(integration, "create_async_httpx_client", lambda hass: None)

    with pytest.raises(ConfigEntryError) as exc_info:
        asyncio.run(integration.async_setup_entry(SimpleNamespace(), _make_entry()))

    assert str(exc_info.value) == ""


def test_successful_auth_continues_setup(monkeypatch):
    integration, ConfigEntryError, _, _ = _load_integration()

    class FakeApi:
        async def async_init(self) -> None:
            return None

        def get_available_vins(self) -> list[str]:
            return []

    monkeypatch.setattr(integration, "create_polestar_api", lambda **kwargs: FakeApi())
    monkeypatch.setattr(integration, "create_async_httpx_client", lambda hass: None)

    with pytest.raises(ConfigEntryError) as exc_info:
        asyncio.run(integration.async_setup_entry(SimpleNamespace(), _make_entry()))

    assert str(exc_info.value) == "No cars found for the provided credentials"


def test_second_account_cannot_reuse_keycloak_session(monkeypatch):
    config_flow = _load_config_flow()
    from pypolestar.exceptions import PolestarAuthFailedException

    shared_client = httpx.AsyncClient()

    class FakeApi:
        def __init__(self, username, password, client_session):
            self.username = username
            self.password = password
            self.client_session = client_session
            self.vins = []

        async def async_init(self) -> None:
            if self.client_session.cookies.get("KC_SESSION") == "valid":
                # A session from the first account satisfies this account.
                self.vins = ["VIN-A"]
                return
            if self.username == "a@example.com" and self.password == "secret":
                self.client_session.cookies.set(
                    "KC_SESSION", "valid", domain="auth.polestar.com"
                )
                self.vins = ["VIN-A"]
                return
            raise PolestarAuthFailedException("Invalid username or password")

        def get_available_vins(self) -> list[str]:
            return self.vins

        async def async_logout(self) -> None:
            return None

    def factory(**kwargs):
        return FakeApi(kwargs["username"], kwargs["password"], kwargs["client_session"])

    monkeypatch.setattr(config_flow, "create_polestar_api", factory)
    monkeypatch.setattr(
        config_flow, "get_async_client", lambda hass: shared_client, raising=False
    )

    flow = config_flow.FlowHandler()
    flow.hass = SimpleNamespace()

    async def scenario():
        try:
            result_a = await flow.async_step_user(
                {"username": "a@example.com", "password": "secret", "vin": None}
            )
            assert result_a["type"] == "create_entry"
            return await flow.async_step_user(
                {"username": "b@example.com", "password": "wrong", "vin": None}
            )
        finally:
            await shared_client.aclose()

    result_b = asyncio.run(scenario())

    assert result_b["errors"] == {"base": "auth_failed"}
    assert shared_client.cookies.get("KC_SESSION") is None
