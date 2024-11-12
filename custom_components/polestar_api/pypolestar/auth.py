import logging
from datetime import datetime, timedelta, timezone
from urllib.parse import urljoin

import httpx

from .const import (
    API_AUTH_URL,
    HTTPX_TIMEOUT,
    OIDC_CLIENT_ID,
    OIDC_PROVIDER_BASE_URL,
    OIDC_REDIRECT_URI,
    TOKEN_REFRESH_WINDOW_MIN,
)
from .exception import PolestarAuthException
from .graphql import QUERY_GET_AUTH_TOKEN, QUERY_REFRESH_AUTH_TOKEN, get_gql_client

_LOGGER = logging.getLogger(__name__)


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
        self.latest_call_code = None
        self.logger = _LOGGER.getChild(unique_id) if unique_id else _LOGGER
        self.gql_client = get_gql_client(url=API_AUTH_URL, client=self.client_session)

    async def async_init(self) -> None:
        await self.update_oidc_configuration()

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

    async def get_token(self, refresh=False) -> None:
        """Get the token from Polestar."""
        # can't use refresh if the token is expired or not set even if refresh is True
        if (
            not refresh
            or self.token_expiry is None
            or self.token_expiry < datetime.now(tz=timezone.utc)
        ):
            if (code := await self._get_code()) is None:
                return

            access_token = None
            operation_name = "getAuthToken"
            query = QUERY_GET_AUTH_TOKEN
            variable_values = {"code": code}
        elif self.refresh_token is None:
            return
        else:
            access_token = self.access_token
            operation_name = "refreshAuthToken"
            query = QUERY_REFRESH_AUTH_TOKEN
            variable_values = {"token": self.refresh_token}

        try:
            async with self.gql_client as client:
                result = await client.execute(
                    query,
                    variable_values=variable_values,
                    extra_args={
                        **(
                            {"headers": {"Authorization": f"Bearer {access_token}"}}
                            if access_token
                            else {}
                        )
                    },
                )
            self.logger.debug("Auth Token Result: %s", result)

            if data := result.get(operation_name):
                self.access_token = data["access_token"]
                self.id_token = data["id_token"]
                self.refresh_token = data["refresh_token"]
                self.token_lifetime = data["expires_in"]
                self.token_expiry = datetime.now(tz=timezone.utc) + timedelta(
                    seconds=self.token_lifetime
                )
                self.latest_call_code = 200
        except Exception as exc:
            self.latest_call_code = None
            self.logger.error("Auth Token Error: %s", str(exc))
            raise PolestarAuthException("Error getting token") from exc

    async def _get_code(self) -> None:
        query_params = await self._get_resume_path()

        # check if code is in query_params
        if query_params.get("code"):
            return query_params.get("code")

        # get the resumePath
        if query_params.get("resumePath"):
            resumePath = query_params.get("resumePath")

        if resumePath is None:
            return

        params = {"client_id": OIDC_CLIENT_ID}
        data = {"pf.username": self.username, "pf.pass": self.password}
        result = await self.client_session.post(
            urljoin(
                OIDC_PROVIDER_BASE_URL,
                f"/as/{resumePath}/resume/as/authorization.ping",
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
            data = {"pf.submit": True, "subject": uid}
            result = await self.client_session.post(
                urljoin(
                    OIDC_PROVIDER_BASE_URL,
                    f"/as/{resumePath}/resume/as/authorization.ping",
                ),
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
        params = {
            "response_type": "code",
            "client_id": OIDC_CLIENT_ID,
            "redirect_uri": OIDC_REDIRECT_URI,
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
