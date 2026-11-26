"""Tests for the Keycloak login shim.

The shim is loaded from its file path so the tests do not import the
Home Assistant dependent package ``__init__``.
"""

from __future__ import annotations

import asyncio
import importlib.util
import sys
from pathlib import Path
from urllib.parse import parse_qs

import httpx
import pytest
from pypolestar.auth import OidcConfiguration

_MODULE_PATH = (
    Path(__file__).parents[1]
    / "custom_components"
    / "polestar_api"
    / "keycloak_auth.py"
)
_spec = importlib.util.spec_from_file_location("polestar_keycloak_auth", _MODULE_PATH)
assert _spec is not None
assert _spec.loader is not None
keycloak_auth = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = keycloak_auth
_spec.loader.exec_module(keycloak_auth)

PING = "https://polestarid.eu.polestar.com"
KC = "https://auth.polestar.com"
CALLBACK = keycloak_auth.OIDC_REDIRECT_URI
LOGIN_ACTION = (
    f"{KC}/realms/polestar/login-actions/authenticate"
    "?session_code=abc&execution=exec-1&client_id=l3oopkc_10&tab_id=tab-1"
)


def _kc_page(page_id: str, summary: str | None = None) -> str:
    """Minimal stand-in for the Keycloak login page with its kcContext."""
    action = LOGIN_ACTION.replace("/", "\\/").replace("&", "&amp;")
    message = (
        f'"message": {{ "summary": "{summary}", "type": "error" }},' if summary else ""
    )
    return f"""<html><script>
    const kcContext = {{
        "url": {{
            "loginAction": "{action}",
            "loginUrl": "\\/realms/polestar/login-actions/authenticate?client_id=x",
        }},
        {message}
        "pageId": "{page_id}",
    }};
    </script></html>"""


class FakePolestarId:
    """Mock transport: PingFederate -> Keycloak -> PingFederate -> app redirect."""

    def __init__(
        self,
        password: str = "secret",
        after_password: str | None = None,
        legacy: bool = False,
    ) -> None:
        self.password = password
        self.after_password = after_password
        self.legacy = legacy
        self.login_form: dict[str, list[str]] | None = None
        self.state: str | None = None

    def __call__(self, request: httpx.Request) -> httpx.Response:
        url = request.url

        if url.path == "/as/authorization.oauth2":
            self.state = url.params.get("state")
            if self.legacy:
                return httpx.Response(
                    200,
                    text='<html><script>url: "/as/resume/as/authorization.ping"</script></html>',
                )
            return httpx.Response(
                302,
                headers={
                    "location": f"{KC}/realms/polestar/protocol/openid-connect/auth?x=1"
                },
            )

        if url.host == "auth.polestar.com" and url.path.endswith(
            "/openid-connect/auth"
        ):
            return httpx.Response(200, text=_kc_page("login"))

        if request.method == "POST" and url.path.endswith(
            "/login-actions/authenticate"
        ):
            assert url.params["session_code"] == "abc"
            self.login_form = parse_qs(request.content.decode(), keep_blank_values=True)
            if self.login_form.get("password") != [self.password]:
                return httpx.Response(
                    200, text=_kc_page("login", "Invalid username or password.")
                )
            if self.after_password:
                return httpx.Response(200, text=_kc_page(self.after_password))
            return httpx.Response(
                302,
                headers={"location": f"{PING}/sp/abc/cb.openid?code=kc-code&state=kc"},
            )

        if url.path == "/sp/abc/cb.openid":
            return httpx.Response(
                302,
                headers={
                    "location": ("/as/resume/as/xyz/resume/as/authorization.ping")
                },
            )

        if request.method == "POST" and url.path == "/as/resume/as/authorization.ping":
            form = parse_qs(request.content.decode())
            if form.get("pf.pass") != [self.password]:
                return httpx.Response(
                    200, text='<html><script>authMessage: "ERR001"</script></html>'
                )
            return httpx.Response(
                302,
                headers={"location": f"{CALLBACK}?code=legacy-code&state={self.state}"},
            )

        if request.method == "GET" and url.path.endswith(
            "/resume/as/authorization.ping"
        ):
            return httpx.Response(
                302,
                headers={"location": f"{CALLBACK}?code=app-code&state={self.state}"},
            )

        if url.path == "/as/token.oauth2":
            form = parse_qs(request.content.decode())
            assert form["grant_type"] == ["authorization_code"]
            assert form["code"] in (["app-code"], ["legacy-code"])
            return httpx.Response(
                200,
                json={
                    "access_token": "at",
                    "refresh_token": "rt",
                    "expires_in": 3600,
                },
            )

        if url.path == "/sign-in-callback":
            return httpx.Response(200, text="signed in")

        if request.method == "GET":
            return httpx.Response(200, text="ok")

        return httpx.Response(404, text=f"unexpected {request.method} {url}")


def _auth(client: httpx.AsyncClient, password: str = "secret"):
    auth = keycloak_auth.KeycloakPolestarAuth("user@example.com", password, client)
    auth.oidc_configuration = OidcConfiguration(
        issuer=PING,
        token_endpoint=f"{PING}/as/token.oauth2",
        authorization_endpoint=f"{PING}/as/authorization.oauth2",
    )
    return auth


def _run(server: FakePolestarId, password: str = "secret"):
    async def scenario():
        async with httpx.AsyncClient(transport=httpx.MockTransport(server)) as client:
            auth = _auth(client, password)
            await auth.get_token()
            return auth, client

    return asyncio.run(scenario())


def test_keycloak_login_gets_tokens():
    server = FakePolestarId()
    auth, client = _run(server)

    assert auth.access_token == "at"
    assert auth.refresh_token == "rt"
    assert server.login_form is not None
    assert server.login_form["username"] == ["user@example.com"]
    assert server.login_form["credentialId"] == [""]


def test_keycloak_wrong_password():
    server = FakePolestarId()

    with pytest.raises(
        keycloak_auth.PolestarAuthFailedException,
        match="Invalid username or password",
    ):
        _run(server, password="wrong")


def test_keycloak_one_time_code_is_reported():
    server = FakePolestarId(after_password="login-otp")

    with pytest.raises(keycloak_auth.PolestarMfaRequiredException, match="login-otp"):
        _run(server)


def test_mfa_error_is_an_auth_failure():
    assert issubclass(
        keycloak_auth.PolestarMfaRequiredException,
        keycloak_auth.PolestarAuthFailedException,
    )


def test_legacy_pingfederate_login_still_works():
    server = FakePolestarId(legacy=True)
    auth, client = _run(server)

    assert auth.access_token == "at"


def test_unescape_js_url():
    assert (
        keycloak_auth._unescape_js_url("https:\\/\\/a.b\\/c?x=1&amp;y=2")
        == "https://a.b/c?x=1&y=2"
    )
