from datetime import datetime, timedelta
import json
import logging

import httpx

from .exception import PolestarAuthException

_LOGGER = logging.getLogger(__name__)


class PolestarAuth:
    """base class for Polestar authentication."""

    def __init__(self, username: str, password: str) -> None:
        self.username = username
        self.password = password
        self.access_token = None
        self.refresh_token = None
        self.token_expiry = None
        self.latest_call_code = None
        self._client_session = httpx.AsyncClient()

    async def get_token(self, refresh=False) -> None:
        # get access / refresh token
        headers = {"Content-Type": "application/json"}
        operationName = "getAuthToken"
        if not refresh:
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
        result = await self._client_session.get("https://pc-api.polestar.com/eu-north-1/auth/", params=params, headers=headers)
        self.latest_call_code = result.status_code
        resultData = result.json()
        if result.status_code != 200 or ("errors" in resultData and len(resultData["errors"])):
            raise PolestarAuthException("Error getting token", result.status_code)
        _LOGGER.debug(resultData)

        if resultData['data']:
            self.access_token = resultData['data'][operationName]['access_token']
            self.refresh_token = resultData['data'][operationName]['refresh_token']
            self.token_expiry = datetime.now(
            ) + timedelta(seconds=resultData['data'][operationName]['expires_in'])
            # ID Token

        _LOGGER.debug(f"Response {self.access_token}")

    async def _get_code(self) -> None:
        query_params = await self._get_resume_path()

        # check if code is in query_params
        if query_params.get('code'):
            return query_params.get('code')[0]

        # get the resumePath
        if query_params.get('resumePath'):
            resumePath = query_params.get('resumePath')

        if resumePath is None:
            return

        params = {
            'client_id': 'polmystar'
        }
        data = {
            'pf.username': self.username,
            'pf.pass': self.password
        }
        result = await self._client_session.post(
            f"https://polestarid.eu.polestar.com/as/{resumePath}/resume/as/authorization.ping",
            params=params,
            data=data
        )
        self.latest_call_code = result.status_code
        if result.status_code != 302:
            raise PolestarAuthException("Error getting code", result.status_code)

        # get the realUrl
        url = result.url
        code = result.next_request.url.params.get('code')

        # sign-in-callback
        result = await self._client_session.get(result.next_request.url)
        self.latest_call_code = result.status_code

        if result.status_code != 200:
            raise PolestarAuthException("Error getting code callback", result.status_code)

        # url encode the code
        result = await self._client_session.get(url)
        self.latest_call_code = result.status_code

        return code

    async def _get_resume_path(self):
        # Get Resume Path
        params = {
            "response_type": "code",
            "client_id": "polmystar",
            "redirect_uri": "https://www.polestar.com/sign-in-callback"
        }
        result = await self._client_session.get("https://polestarid.eu.polestar.com/as/authorization.oauth2", params=params)
        if result.status_code != 303:
            raise PolestarAuthException("Error getting resume path ", result.status_code)
        return result.next_request.url.params
