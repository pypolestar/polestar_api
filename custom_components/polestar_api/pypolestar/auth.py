import base64
import hashlib
import logging
import os
from datetime import datetime, timedelta, timezone
from urllib.parse import urljoin, urlparse

import httpx

from .const import (
    HTTPX_TIMEOUT,
    OIDC_CLIENT_ID,
    OIDC_COOKIES,
    OIDC_PROVIDER_BASE_URL,
    OIDC_REDIRECT_URI,
    OIDC_SCOPE,
    TOKEN_REFRESH_WINDOW_MIN,
)
from .exception import PolestarAuthException

_LOGGER = logging.getLogger(__name__)


def b64urlencode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


class PolestarAuth:
    """base class for Polestar authentication."""

    def __init__(
        self,
        username: str,
        password: str,
        client_session: httpx.AsyncClient,
        unique_id: str | None = None,
    ) -> None:
        """Initialize the Polestar authentication."""
        self.username = username
        self.password = password
        self.client_session = client_session

        self.access_token = None
        self.id_token = None
        self.refresh_token = None
        self.token_lifetime = None
        self.token_expiry = None

        self.oidc_configuration = {}
        self.oidc_provider = OIDC_PROVIDER_BASE_URL
        self.oidc_code_verifier: str | None = None
        self.oidc_state: str | None = None

        self.latest_call_code = None
        self.logger = _LOGGER.getChild(unique_id) if unique_id else _LOGGER

    async def async_init(self) -> None:
        await self.update_oidc_configuration()

    async def async_logout(self) -> None:
        self.logger.debug("Logout")

        domain = urlparse(OIDC_PROVIDER_BASE_URL).hostname
        for name in OIDC_COOKIES:
            self.logger.debug("Delete cookie %s in domain %s", name, domain)
            self.client_session.cookies.delete(name=name, domain=domain)

        self.access_token = None
        self.id_token = None
        self.refresh_token = None
        self.token_lifetime = None
        self.token_expiry = None

        self.oidc_code_verifier = None
        self.oidc_state = None

    async def update_oidc_configuration(self) -> None:
        result = await self.client_session.get(
            urljoin(OIDC_PROVIDER_BASE_URL, "/.well-known/openid-configuration")
        )
        result.raise_for_status()
        self.oidc_configuration = result.json()

    def need_token_refresh(self) -> bool:
        """Return True if token needs refresh"""
        if self.token_expiry is None:
            raise PolestarAuthException("No token expiry found")
        refresh_window = min([(self.token_lifetime or 0) / 2, TOKEN_REFRESH_WINDOW_MIN])
        expires_in = (self.token_expiry - datetime.now(tz=timezone.utc)).total_seconds()
        if expires_in < refresh_window:
            self.logger.debug(
                "Token expires in %d seconds, time to refresh", expires_in
            )
            return True
        return False

    def is_token_valid(self) -> bool:
        return (
            self.access_token is not None
            and self.token_expiry is not None
            and self.token_expiry > datetime.now(tz=timezone.utc)
        )

    async def get_token(self, force: bool = False) -> None:
        """Ensure we have a valid access token (still valid, refreshed or initial)."""

        if (
            not force
            and self.access_token is not None
            and self.token_expiry
            and self.token_expiry > datetime.now(tz=timezone.utc)
        ):
            self.logger.debug("Token still valid until %s", self.token_expiry)
            return

        if self.refresh_token:
            try:
                await self._token_refresh()
                self.logger.debug("Token refreshed")
            except PolestarAuthException:
                self.logger.warning("Unable to refresh token, retry with code")

        try:
            await self._authorization_code()
            self.logger.debug("Initial token acquired")
            return
        except PolestarAuthException as exc:
            raise PolestarAuthException("Unable to acquire initial token") from exc

    def _parse_token_response(self, response: httpx.Response) -> None:
        """Parse response from token endpoint and update token state."""

        self.latest_call_code = response.status_code

        payload = response.json()

        if "error" in payload:
            self.logger.error("Token error: %s", payload)
            raise PolestarAuthException("Token error", response.status_code)

        self.access_token = payload["access_token"]
        self.refresh_token = payload["refresh_token"]
        self.token_lifetime = payload["expires_in"]
        self.token_expiry = datetime.now(tz=timezone.utc) + timedelta(
            seconds=self.token_lifetime
        )

        self.logger.debug("Access token updated, valid until %s", self.token_expiry)

    async def _authorization_code(self) -> None:
        """Get initial token via authorization code."""

        if (code := await self._get_code()) is None:
            raise PolestarAuthException("Unable to get code")

        token_request = {
            "grant_type": "authorization_code",
            "client_id": OIDC_CLIENT_ID,
            "code": code,
            "redirect_uri": OIDC_REDIRECT_URI,
            **(
                {"code_verifier": self.oidc_code_verifier}
                if self.oidc_code_verifier
                else {}
            ),
        }

        self.logger.debug(
            "Call token endpoint with grant_type=%s", token_request["grant_type"]
        )

        response = await self.client_session.post(
            self.oidc_configuration["token_endpoint"],
            data=token_request,
            timeout=HTTPX_TIMEOUT,
        )

        self._parse_token_response(response)

    async def _token_refresh(self) -> None:
        """Refresh existing token."""

        token_request = {
            "grant_type": "refresh_token",
            "client_id": OIDC_CLIENT_ID,
            "refresh_token": self.refresh_token,
        }

        self.logger.debug(
            "Call token endpoint with grant_type=%s", token_request["grant_type"]
        )

        response = await self.client_session.post(
            self.oidc_configuration["token_endpoint"],
            data=token_request,
            timeout=HTTPX_TIMEOUT,
        )

        self._parse_token_response(response)

    async def _get_code(self) -> str | None:
        query_params = await self._get_resume_path()

        # check if code is in query_params
        if code := query_params.get("code"):
            return code

        # get the resume path
        if not (resume_path := query_params.get("resumePath")):
            self.logger.warning("Missing resumePath in authorization response")
            return

        params = {"client_id": OIDC_CLIENT_ID}
        data = {"pf.username": self.username, "pf.pass": self.password}
        result = await self.client_session.post(
            urljoin(
                OIDC_PROVIDER_BASE_URL,
                f"/as/{resume_path}/resume/as/authorization.ping",
            ),
            params=params,
            data=data,
        )
        if result.status_code not in [302, 303]:
            self.latest_call_code = result.status_code
            raise PolestarAuthException("Error getting code", result.status_code)

        # get the realUrl
        url = result.url
        code = result.next_request.url.params.get("code")
        uid = result.next_request.url.params.get("uid")

        # handle missing code (e.g., accepting terms and conditions)
        if code is None and uid:
            self.logger.debug(
                "Code missing; submit confirmation for uid=%s and retry", uid
            )
            params = {"client_id": OIDC_CLIENT_ID}
            data = {"pf.submit": True, "subject": uid}
            result = await self.client_session.post(
                urljoin(
                    OIDC_PROVIDER_BASE_URL,
                    f"/as/{resume_path}/resume/as/authorization.ping",
                ),
                params=params,
                data=data,
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

    async def _get_resume_path(self):
        """Get Resume Path from Polestar."""

        self.oidc_state = self.get_state()

        params = {
            "response_type": "code",
            "client_id": OIDC_CLIENT_ID,
            "redirect_uri": OIDC_REDIRECT_URI,
            "state": self.oidc_state,
            "code_challenge_method": "S256",
            "code_challenge": self.get_code_challenge(),
            "scope": OIDC_SCOPE,
        }

        result = await self.client_session.get(
            self.oidc_configuration["authorization_endpoint"],
            params=params,
            timeout=HTTPX_TIMEOUT,
        )
        self.latest_call_code = result.status_code

        if result.status_code in (303, 302):
            return result.next_request.url.params

        self.logger.error("Error: %s", result.text)
        raise PolestarAuthException("Error getting resume path ", result.status_code)

    @staticmethod
    def get_state() -> str:
        return b64urlencode(os.urandom(32))

    @staticmethod
    def get_code_verifier() -> str:
        return b64urlencode(os.urandom(32))

    def get_code_challenge(self) -> str:
        self.oidc_code_verifier = self.get_code_verifier()
        m = hashlib.sha256()
        m.update(self.oidc_code_verifier.encode())
        return b64urlencode(m.digest())
