"""Keycloak login support for pypolestar.

Since 26 November 2026 the Polestar ID authorization endpoint redirects to a
Keycloak realm on ``auth.polestar.com``. pypolestar 1.12.7 only understands the
legacy PingFederate login form, so every login fails with
"Error getting resume path".

This module adds the Keycloak flow from
https://github.com/kildahldev/unofficial-polestar-api/pull/47. It can be removed
once a pypolestar release includes the same support.
"""

from __future__ import annotations

import html
import logging
import re
from typing import TYPE_CHECKING
from urllib.parse import parse_qs, urljoin, urlparse

from pypolestar import PolestarApi
from pypolestar.auth import PolestarAuth
from pypolestar.const import HTTPX_TIMEOUT, OIDC_PROVIDER_BASE_URL, OIDC_REDIRECT_URI
from pypolestar.exceptions import PolestarAuthException, PolestarAuthFailedException

if TYPE_CHECKING:
    import httpx

_LOGGER = logging.getLogger(__name__)

_REDIRECT_STATUS_CODES = frozenset({301, 302, 303, 307, 308})
_MAX_REDIRECTS = 10

# Keycloak embeds its page state in a kcContext object.
_KC_LOGIN_ACTION_RE = re.compile(r'"loginAction":\s*"([^"]+)"')
_KC_PAGE_ID_RE = re.compile(r'"pageId":\s*"([^"]+)"')
_KC_INVALID_CREDENTIALS = "Invalid username or password"

# Legacy PingFederate login form (same expression as pypolestar.auth).
_PF_RESUME_RE = re.compile(r'(?:url|action):\s*"(.+)"')


class PolestarMfaRequiredException(PolestarAuthFailedException):
    """Polestar ID requires an interactive step, such as a one-time code."""


def _unescape_js_url(value: str) -> str:
    """Undo the JS/HTML escaping Keycloak applies to URLs in kcContext."""
    return html.unescape(value.replace("\\/", "/"))


def _kc_page_id(text: str) -> str | None:
    match = _KC_PAGE_ID_RE.search(text)
    return match.group(1) if match else None


def _auth_code(url: str) -> str | None:
    """Return the authorization code from a redirect URL, if present."""
    return parse_qs(urlparse(url).query).get("code", [None])[0]


def _is_callback_url(url: str) -> bool:
    """Return whether the URL is the OIDC redirect URI."""
    target = urlparse(url)
    callback = urlparse(OIDC_REDIRECT_URI)
    return (target.scheme, target.netloc, target.path) == (
        callback.scheme,
        callback.netloc,
        callback.path,
    )


class KeycloakPolestarAuth(PolestarAuth):
    """PolestarAuth with support for the Keycloak login page."""

    async def _get_code(self) -> str | None:
        page, code = await self._get_authorization_page()
        if code is not None:
            return code

        if match := _KC_LOGIN_ACTION_RE.search(page.text):
            self.logger.debug("Polestar ID redirected to Keycloak")
            login_action = urljoin(str(page.url), _unescape_js_url(match.group(1)))
            return await self._get_keycloak_code(login_action)

        return await self._get_pingfederate_code(page)

    async def _get_authorization_page(self) -> tuple[httpx.Response, str | None]:
        """Load the login page, following the redirect to Keycloak if needed."""
        if not self.oidc_configuration:
            raise PolestarAuthException(message="No OIDC configuration")

        self.oidc_state = self.get_state()
        response = await self.client_session.get(
            self.oidc_configuration.authorization_endpoint,
            params=self.get_params(),
            follow_redirects=False,
            timeout=HTTPX_TIMEOUT,
        )
        self.latest_call_code = response.status_code

        redirects = 0
        while (
            response.status_code in _REDIRECT_STATUS_CODES
            and redirects < _MAX_REDIRECTS
        ):
            location = response.headers.get("location")
            if not location:
                break
            location = urljoin(str(response.url), location)

            if _is_callback_url(location):
                return response, _auth_code(location)
            if urlparse(location).scheme not in {"http", "https"}:
                break

            response = await self.client_session.get(location, timeout=HTTPX_TIMEOUT)
            self.latest_call_code = response.status_code
            redirects += 1

        return response, _auth_code(str(response.url))

    async def _get_keycloak_code(self, login_action: str) -> str:
        """Log in on the Keycloak page and follow the redirects to the code."""
        response = await self.client_session.post(
            login_action,
            data={
                "username": self.username,
                "password": self.password,
                "credentialId": "",
            },
            follow_redirects=False,
            timeout=HTTPX_TIMEOUT,
        )
        self.latest_call_code = response.status_code
        self._raise_for_keycloak_page(response)

        redirects = 0
        while response.status_code in _REDIRECT_STATUS_CODES:
            if redirects >= _MAX_REDIRECTS:
                raise PolestarAuthException("Too many redirects after Keycloak login")

            location = response.headers.get("location")
            if not location:
                break
            location = urljoin(str(response.url), location)

            if _is_callback_url(location):
                if code := _auth_code(location):
                    return code
                break
            if urlparse(location).scheme not in {"http", "https"}:
                break

            response = await self.client_session.get(
                location, follow_redirects=False, timeout=HTTPX_TIMEOUT
            )
            self.latest_call_code = response.status_code
            self._raise_for_keycloak_page(response)
            redirects += 1

        raise PolestarAuthException(
            f"No auth code after Keycloak login (status {response.status_code})",
            response.status_code,
        )

    def _raise_for_keycloak_page(self, response: httpx.Response) -> None:
        """Translate a non-redirect Keycloak response into an auth error."""
        if response.status_code in _REDIRECT_STATUS_CODES:
            return

        if _KC_INVALID_CREDENTIALS in response.text:
            raise PolestarAuthFailedException("Invalid username or password")

        page_id = _kc_page_id(response.text)
        if page_id and page_id != "login":
            # e.g. a one-time code sent by SMS or e-mail
            raise PolestarMfaRequiredException(
                "Polestar ID asked for an additional step after the password "
                f"({page_id}), e.g. a one-time code. Sign in once at "
                "polestar.com with the same account, then retry."
            )

        raise PolestarAuthException(
            f"Keycloak login failed (status {response.status_code}, "
            f"page {page_id or 'unknown'})",
            response.status_code,
        )

    async def _get_pingfederate_code(self, page: httpx.Response) -> str | None:
        """Legacy PingFederate login, mirrors pypolestar 1.12.7."""
        if not (match := _PF_RESUME_RE.search(page.text)):
            self.logger.error("Error: %s", page.text)
            raise PolestarAuthException("Error getting resume path", page.status_code)

        resume_path = match.group(1)
        result = await self.client_session.post(
            urljoin(OIDC_PROVIDER_BASE_URL, resume_path),
            params=self.get_params(),
            data={"pf.username": self.username, "pf.pass": self.password},
            follow_redirects=False,
        )

        if result.status_code not in (302, 303):
            self.latest_call_code = result.status_code
            if 'authMessage: "ERR001"' in result.text:
                raise PolestarAuthFailedException(
                    "Authentication error (ERR001), invalid username/password"
                )
            raise PolestarAuthException("Error getting code", result.status_code)

        if result.next_request is None:
            raise PolestarAuthException("Missing next request in 3xx response")

        url = result.url
        code = result.next_request.url.params.get("code")
        uid = result.next_request.url.params.get("uid")

        # handle missing code (e.g., accepting terms and conditions)
        if code is None and uid:
            self.logger.debug(
                "Code missing; submit confirmation for uid=%s and retry", uid
            )
            result = await self.client_session.post(
                urljoin(OIDC_PROVIDER_BASE_URL, resume_path),
                params=self.get_params(),
                data={"pf.submit": True, "subject": uid},
                follow_redirects=False,
            )
            url = result.url
            code = result.next_request.url.params.get("code")

        # sign-in-callback
        result = await self.client_session.get(
            result.next_request.url, timeout=HTTPX_TIMEOUT
        )
        self.latest_call_code = result.status_code

        if result.status_code != 200:
            self.logger.error("Auth Code Error: %s", result)
            raise PolestarAuthException(
                "Error getting code callback", result.status_code
            )

        result = await self.client_session.get(url)

        return code


def create_polestar_api(
    username: str,
    password: str,
    client_session: httpx.AsyncClient | None = None,
    vins: list[str] | None = None,
    unique_id: str | None = None,
    public_api_key: str | None = None,
    enable_grpc: bool = True,
) -> PolestarApi:
    """Create a PolestarApi client that uses the Keycloak-capable auth flow."""
    api = PolestarApi(
        username=username,
        password=password,
        client_session=client_session,
        vins=vins,
        unique_id=unique_id,
        public_api_key=public_api_key,
        enable_grpc=enable_grpc,
    )
    api.auth = KeycloakPolestarAuth(
        username=username,
        password=password,
        client_session=api.client_session,
        unique_id=unique_id,
    )
    return api
