import json
import logging
from datetime import datetime, timedelta

import httpx

from .const import HTTPX_TIMEOUT
from .exception import PolestarAuthException

_LOGGER = logging.getLogger(__name__)


class PolestarAuth:
    """base class for Polestar authentication."""

    def __init__(
        self, username: str, password: str, client_session: httpx.AsyncClient
    ) -> None:
        """Initialize the Polestar authentication."""
        self.username = username
        self.password = password
        self.client_session = client_session
        self.access_token = None
        self.refresh_token = None
        self.token_expiry = None
        self.latest_call_code = None

    async def get_token(self, refresh=False) -> None:
        """Get the token from Polestar."""
        headers = {"Content-Type": "application/json"}
        operationName = "getAuthToken"
        # can't use refresh if the token is expired or not set even if refresh is True
        if (
            not refresh
            or self.token_expiry is None
            or self.token_expiry < datetime.now()
        ):
            code = await self._get_code()
            if code is None:
                return
            params = {
                "query": "query getAuthToken($code: String!) { getAuthToken(code: $code) { id_token access_token refresh_token expires_in }}",
                "operationName": operationName,
                "variables": json.dumps({"code": code}),
            }
        else:
            if self.refresh_token is None:
                return
            token = self.refresh_token
            operationName = "refreshAuthToken"
            headers["Authorization"] = f"Bearer {self.access_token}"

            params = {
                "query": "query refreshAuthToken($token: String!) { refreshAuthToken(token: $token) { id_token access_token refresh_token expires_in }}",
                "operationName": operationName,
                "variables": json.dumps({"token": token}),
            }
        result = await self.client_session.get(
            "https://pc-api.polestar.com/eu-north-1/auth/",
            params=params,
            headers=headers,
            timeout=HTTPX_TIMEOUT,
        )
        self.latest_call_code = result.status_code
        resultData = result.json()
        if result.status_code != 200 or (
            "errors" in resultData and len(resultData["errors"])
        ):
            _LOGGER.error(result)
            raise PolestarAuthException("Error getting token", result.status_code)
        _LOGGER.debug(resultData)

        if resultData["data"]:
            self.access_token = resultData["data"][operationName]["access_token"]
            self.refresh_token = resultData["data"][operationName]["refresh_token"]
            self.token_expiry = datetime.now() + timedelta(
                seconds=resultData["data"][operationName]["expires_in"]
            )
            # ID Token

        _LOGGER.debug(f"Response {self.access_token}")

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

        params = {"client_id": "polmystar"}
        data = {"pf.username": self.username, "pf.pass": self.password}
        result = await self.client_session.post(
            f"https://polestarid.eu.polestar.com/as/{resumePath}/resume/as/authorization.ping",
            params=params,
            data=data,
        )
        self.latest_call_code = result.status_code
        if result.status_code != 302:
            raise PolestarAuthException("Error getting code", result.status_code)

        # get the realUrl
        url = result.url
        code = result.next_request.url.params.get("code")

        # sign-in-callback
        result = await self.client_session.get(
            result.next_request.url, timeout=HTTPX_TIMEOUT
        )
        self.latest_call_code = result.status_code

        if result.status_code != 200:
            _LOGGER.error(result)
            raise PolestarAuthException(
                "Error getting code callback", result.status_code
            )

        # url encode the code
        result = await self.client_session.get(url)
        self.latest_call_code = result.status_code

        return code

    async def _get_resume_path(self):
        """Get Resume Path from Polestar."""
        params = {
            "response_type": "code",
            "client_id": "polmystar",
            "redirect_uri": "https://www.polestar.com/sign-in-callback",
        }
        result = await self.client_session.get(
            "https://polestarid.eu.polestar.com/as/authorization.oauth2",
            params=params,
            timeout=HTTPX_TIMEOUT,
        )
        if result.status_code in (303, 302):
            return result.next_request.url.params

        _LOGGER.error(result.text)
        raise PolestarAuthException("Error getting resume path ", result.status_code)
