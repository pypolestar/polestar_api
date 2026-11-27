"""Tests for config entry setup error handling."""

from __future__ import annotations

import asyncio
import sys
import types
from types import SimpleNamespace

import httpx
import pytest


class _FakeSession:
    """Minimal stand-in for the HTTP client used during setup."""

    def __init__(self) -> None:
        self.closed = False

    async def aclose(self) -> None:
        self.closed = True


class _FakeApiBase:
    """Base fake API with the cleanup method that setup calls."""

    async def async_logout(self) -> None:
        return None


class _FakeApiClient(_FakeApiBase):
    """Stand-in for PolestarApi with the methods used on unload."""

    def __init__(self, session: _FakeSession, fail_logout: bool = False) -> None:
        self.client_session = session
        self.logged_out = False
        self.fail_logout = fail_logout

    async def async_logout(self) -> None:
        if self.fail_logout:
            raise RuntimeError("logout failed")
        self.logged_out = True


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

    ssl_util = module("homeassistant.util.ssl")
    ssl_util.client_context = lambda *args, **kwargs: None

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

    class ConfigEntryNotReady(HomeAssistantError):
        pass

    exceptions.HomeAssistantError = HomeAssistantError
    exceptions.ConfigEntryError = ConfigEntryError
    exceptions.ConfigEntryAuthFailed = ConfigEntryAuthFailed
    exceptions.ConfigEntryNotReady = ConfigEntryNotReady

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
    httpx_client.create_async_httpx_client = lambda hass, **kwargs: _FakeSession()

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

    import custom_components.polestar_api as integration

    return integration


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


def _patch_http_client(monkeypatch, integration) -> _FakeSession:
    """Replace the config entry HTTP client with a closable fake."""
    session = _FakeSession()
    monkeypatch.setattr(integration, "_create_client_session", lambda: session)
    return session


def test_mfa_message_is_preserved_in_setup_error(monkeypatch):
    integration = _load_integration()

    from homeassistant.exceptions import ConfigEntryAuthFailed

    from custom_components.polestar_api.keycloak_auth import (
        PolestarMfaRequiredException,
    )

    class FakeApi(_FakeApiBase):
        async def async_init(self) -> None:
            raise PolestarMfaRequiredException("Sign in once at polestar.com")

    monkeypatch.setattr(integration, "create_polestar_api", lambda **kwargs: FakeApi())
    session = _patch_http_client(monkeypatch, integration)

    with pytest.raises(ConfigEntryAuthFailed) as exc_info:
        asyncio.run(integration.async_setup_entry(SimpleNamespace(), _make_entry()))

    assert str(exc_info.value) == "Sign in once at polestar.com"
    assert session.closed is True


def test_failed_auth_keeps_empty_setup_error(monkeypatch):
    integration = _load_integration()

    from homeassistant.exceptions import ConfigEntryAuthFailed
    from pypolestar.exceptions import PolestarAuthFailedException

    class FakeApi(_FakeApiBase):
        async def async_init(self) -> None:
            raise PolestarAuthFailedException("bad password")

    monkeypatch.setattr(integration, "create_polestar_api", lambda **kwargs: FakeApi())
    session = _patch_http_client(monkeypatch, integration)

    with pytest.raises(ConfigEntryAuthFailed) as exc_info:
        asyncio.run(integration.async_setup_entry(SimpleNamespace(), _make_entry()))

    assert str(exc_info.value) == ""
    assert session.closed is True


def test_successful_auth_continues_setup(monkeypatch):
    integration = _load_integration()

    from homeassistant.exceptions import ConfigEntryError

    class FakeApi(_FakeApiBase):
        async def async_init(self) -> None:
            return None

        def get_available_vins(self) -> list[str]:
            return []

    monkeypatch.setattr(integration, "create_polestar_api", lambda **kwargs: FakeApi())
    session = _patch_http_client(monkeypatch, integration)

    with pytest.raises(ConfigEntryError) as exc_info:
        asyncio.run(integration.async_setup_entry(SimpleNamespace(), _make_entry()))

    assert str(exc_info.value) == "No cars found for the provided credentials"
    assert session.closed is True


def test_unavailable_auth_service_is_retried_at_setup(monkeypatch):
    integration = _load_integration()

    from homeassistant.exceptions import ConfigEntryNotReady
    from pypolestar.exceptions import PolestarAuthException

    class FakeApi(_FakeApiBase):
        async def async_init(self) -> None:
            # pypolestar wraps transport and server failures in this exception.
            raise PolestarAuthException("Unable to acquire initial token")

    monkeypatch.setattr(integration, "create_polestar_api", lambda **kwargs: FakeApi())
    session = _patch_http_client(monkeypatch, integration)

    with pytest.raises(ConfigEntryNotReady) as exc_info:
        asyncio.run(integration.async_setup_entry(SimpleNamespace(), _make_entry()))

    assert str(exc_info.value) == "Unable to acquire initial token"
    assert session.closed is True


def test_connection_error_is_retried_at_setup(monkeypatch):
    integration = _load_integration()

    from homeassistant.exceptions import ConfigEntryNotReady

    class FakeApi(_FakeApiBase):
        async def async_init(self) -> None:
            raise httpx.ConnectError("dns down")

    monkeypatch.setattr(integration, "create_polestar_api", lambda **kwargs: FakeApi())
    session = _patch_http_client(monkeypatch, integration)

    with pytest.raises(ConfigEntryNotReady) as exc_info:
        asyncio.run(integration.async_setup_entry(SimpleNamespace(), _make_entry()))

    assert str(exc_info.value) == "dns down"
    assert session.closed is True


def test_unload_closes_the_http_client():
    integration = _load_integration()
    session = _FakeSession()
    api_client = _FakeApiClient(session)
    entry = _make_entry()
    entry.runtime_data = SimpleNamespace(api_client=api_client)

    async def async_unload_platforms(config_entry, platforms) -> bool:
        return True

    hass = SimpleNamespace(
        config_entries=SimpleNamespace(async_unload_platforms=async_unload_platforms)
    )

    assert asyncio.run(integration.async_unload_entry(hass, entry)) is True
    assert api_client.logged_out is True
    assert session.closed is True


def test_failed_unload_keeps_the_http_client():
    integration = _load_integration()
    session = _FakeSession()
    api_client = _FakeApiClient(session)
    entry = _make_entry()
    entry.runtime_data = SimpleNamespace(api_client=api_client)

    async def async_unload_platforms(config_entry, platforms) -> bool:
        return False

    hass = SimpleNamespace(
        config_entries=SimpleNamespace(async_unload_platforms=async_unload_platforms)
    )

    assert asyncio.run(integration.async_unload_entry(hass, entry)) is False
    assert api_client.logged_out is False
    assert session.closed is False


def test_logout_error_does_not_block_the_client_close():
    integration = _load_integration()
    session = _FakeSession()
    api_client = _FakeApiClient(session, fail_logout=True)
    entry = _make_entry()
    entry.runtime_data = SimpleNamespace(api_client=api_client)

    async def async_unload_platforms(config_entry, platforms) -> bool:
        return True

    hass = SimpleNamespace(
        config_entries=SimpleNamespace(async_unload_platforms=async_unload_platforms)
    )

    assert asyncio.run(integration.async_unload_entry(hass, entry)) is True
    assert session.closed is True


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


def _make_flow_with_reauth_entry(entry: SimpleNamespace):
    """Build a config flow that reauthenticates the given entry."""
    config_flow = _load_config_flow()
    flow = config_flow.FlowHandler()
    flow.hass = SimpleNamespace()
    flow.abort_calls = []

    # Patch on the instance, not on the stub class: when Home Assistant is
    # installed the real ConfigFlow reads the entry from the flow context.
    def record_abort(target, *, data_updates=None, **_kwargs):
        flow.abort_calls.append({"entry": target, "data_updates": data_updates})
        return {"type": "abort", "reason": "reauth_successful", "entry": target}

    flow._get_reauth_entry = lambda: entry
    flow.async_update_reload_and_abort = record_abort
    return config_flow, flow


def test_reauth_fixture_does_not_depend_on_the_base_flow():
    flow = _make_flow_with_reauth_entry(_make_entry())[1]

    assert "_get_reauth_entry" in vars(flow)
    assert "async_update_reload_and_abort" in vars(flow)


def _patch_api(monkeypatch, config_flow, api_class) -> None:
    """Replace the API factory with a class that takes the same arguments."""
    monkeypatch.setattr(
        config_flow,
        "create_polestar_api",
        lambda **kwargs: api_class(
            kwargs["username"], kwargs["password"], kwargs["client_session"]
        ),
    )


def test_reauth_shows_form_for_the_current_account():
    _, flow = _make_flow_with_reauth_entry(_make_entry())

    result = asyncio.run(
        flow.async_step_reauth({"username": "user", "password": "pass"})
    )

    assert result["type"] == "form"
    assert result["step_id"] == "reauth_confirm"
    assert result["errors"] == {}
    assert result["description_placeholders"] == {"username": "user"}


def test_reauth_updates_credentials_and_reloads(monkeypatch):
    config_flow, flow = _make_flow_with_reauth_entry(_make_entry())
    seen = {}

    class FakeApi:
        def __init__(self, username, password, client_session):
            seen["username"] = username
            seen["password"] = password

        async def async_init(self) -> None:
            if seen["password"] != "new-secret":
                from pypolestar.exceptions import PolestarAuthFailedException

                raise PolestarAuthFailedException("Invalid username or password")

        def get_available_vins(self) -> list[str]:
            return ["VIN123"]

        async def async_logout(self) -> None:
            return None

    _patch_api(monkeypatch, config_flow, FakeApi)

    result = asyncio.run(flow.async_step_reauth_confirm({"password": "new-secret"}))

    assert result["type"] == "abort"
    assert result["reason"] == "reauth_successful"
    assert seen["username"] == "user"
    assert seen["password"] == "new-secret"
    assert len(flow.abort_calls) == 1
    assert flow.abort_calls[0]["entry"].data["username"] == "user"
    assert flow.abort_calls[0]["data_updates"] == {"password": "new-secret"}


def test_reauth_keeps_entry_when_password_is_wrong(monkeypatch):
    entry = _make_entry()
    config_flow, flow = _make_flow_with_reauth_entry(entry)

    class FakeApi:
        def __init__(self, username, password, client_session):
            self.password = password

        async def async_init(self) -> None:
            from pypolestar.exceptions import PolestarAuthFailedException

            raise PolestarAuthFailedException("Invalid username or password")

        def get_available_vins(self) -> list[str]:
            return []

        async def async_logout(self) -> None:
            return None

    _patch_api(monkeypatch, config_flow, FakeApi)

    result = asyncio.run(flow.async_step_reauth_confirm({"password": "wrong"}))

    assert result["type"] == "form"
    assert result["errors"] == {"base": "auth_failed"}
    assert flow.abort_calls == []
    assert entry.data["password"] == "pass"


def test_unavailable_auth_service_is_not_reported_as_a_wrong_password(monkeypatch):
    config_flow, flow = _make_flow_with_reauth_entry(_make_entry())

    class FakeApi:
        def __init__(self, username, password, client_session):
            pass

        async def async_init(self) -> None:
            from pypolestar.exceptions import PolestarAuthException

            # pypolestar wraps transport and server failures in this exception.
            raise PolestarAuthException("Unable to acquire initial token")

        def get_available_vins(self) -> list[str]:
            return []

        async def async_logout(self) -> None:
            return None

    _patch_api(monkeypatch, config_flow, FakeApi)

    result = asyncio.run(flow.async_step_reauth_confirm({"password": "pass"}))

    assert result["type"] == "form"
    assert result["errors"] == {"base": "api"}
    assert flow.abort_calls == []


def test_connection_error_is_reported_as_api_error(monkeypatch):
    config_flow, flow = _make_flow_with_reauth_entry(_make_entry())

    class FakeApi:
        def __init__(self, username, password, client_session):
            pass

        async def async_init(self) -> None:
            raise httpx.ConnectError("dns down")

        def get_available_vins(self) -> list[str]:
            return []

        async def async_logout(self) -> None:
            return None

    _patch_api(monkeypatch, config_flow, FakeApi)

    result = asyncio.run(flow.async_step_reauth_confirm({"password": "pass"}))

    assert result["type"] == "form"
    assert result["errors"] == {"base": "api"}
    assert flow.abort_calls == []


def test_reauth_reports_one_time_code(monkeypatch):
    config_flow, flow = _make_flow_with_reauth_entry(_make_entry())

    class FakeApi:
        def __init__(self, username, password, client_session):
            pass

        async def async_init(self) -> None:
            from custom_components.polestar_api.keycloak_auth import (
                PolestarMfaRequiredException,
            )

            raise PolestarMfaRequiredException("page login-otp")

        def get_available_vins(self) -> list[str]:
            return []

        async def async_logout(self) -> None:
            return None

    _patch_api(monkeypatch, config_flow, FakeApi)

    result = asyncio.run(flow.async_step_reauth_confirm({"password": "pass"}))

    assert result["type"] == "form"
    assert result["errors"] == {"base": "mfa_required"}


def test_reauth_reports_vin_not_found(monkeypatch):
    entry = _make_entry()
    config_flow, flow = _make_flow_with_reauth_entry(entry)

    class FakeApi:
        def __init__(self, username, password, client_session):
            pass

        async def async_init(self) -> None:
            return None

        def get_available_vins(self) -> list[str]:
            return ["OTHER-VIN"]

        async def async_logout(self) -> None:
            return None

    _patch_api(monkeypatch, config_flow, FakeApi)

    result = asyncio.run(flow.async_step_reauth_confirm({"password": "pass"}))

    assert result["errors"] == {"base": "vin_not_found"}
    assert entry.data["password"] == "pass"
