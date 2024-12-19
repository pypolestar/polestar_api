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

    async def get_token(self, refresh=False) -> None:
        """Get the token from Polestar."""

        if (
            not refresh
            or self.token_expiry is None
            or self.token_expiry < datetime.now(tz=timezone.utc)
        ):
            if (code := await self._get_code()) is None:
                return

            token_request = {
                "grant_type": "authorization_code",
                "client_id": OIDC_CLIENT_ID,
                "code": code,
                "redirect_uri": OIDC_REDIRECT_URI,
                **(
                    {
                        "code_verifier": self.oidc_code_verifier,
                    }
                    if self.oidc_code_verifier
                    else {}
                ),
            }

        elif self.refresh_token:
            token_request = {
                "grant_type": "refresh_token",
                "client_id": OIDC_CLIENT_ID,
                "refresh_token": self.refresh_token,
            }
        else:
            return

        self.logger.debug(
            "Call token endpoint with grant_type=%s", token_request["grant_type"]
        )

        try:
            result = await self.client_session.post(
                self.oidc_configuration["token_endpoint"],
                data=token_request,
                timeout=HTTPX_TIMEOUT,
            )
        except Exception as exc:
            self.latest_call_code = None
            self.logger.error("Auth Token Error: %s", str(exc))
            raise PolestarAuthException("Error getting token") from exc

        payload = result.json()
        self.latest_call_code = result.status_code

        try:
            self.access_token = payload["access_token"]
            self.refresh_token = payload["refresh_token"]
            self.token_lifetime = payload["expires_in"]
            self.token_expiry = datetime.now(tz=timezone.utc) + timedelta(
                seconds=self.token_lifetime
            )
        except KeyError as exc:
            self.logger.error("Token response missing expected keys: %s", exc)
            raise PolestarAuthException("Incomplete token response") from exc

        self.logger.debug("Access token updated, valid until %s", self.token_expiry)

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
