from datetime import datetime, timedelta
import logging
import json
from urllib.parse import parse_qs, urlparse
import aiohttp

_LOGGER = logging.getLogger(__name__)


class PolestarAuth:
    """ base class for Polestar authentication"""

    def __init__(self, username: str, password: str) -> None:
        self.username = username
        self.password = password
        self.access_token = None
        self.refresh_token = None
        self.token_expiry = None
        self.latest_call_code = None
        self.session = aiohttp.ClientSession()

    async def get_token(self) -> None:
        code = await self._get_code()
        if code is None:
            return

        # get token
        params = {
            "query": "query getAuthToken($code: String!) { getAuthToken(code: $code) { id_token access_token refresh_token expires_in }}",
            "operationName": "getAuthToken",
            "variables": json.dumps({"code": code})
        }

        headers = {
            "Content-Type": "application/json"
        }
        result = await self.session.get("https://pc-api.polestar.com/eu-north-1/auth/", params=params, headers=headers)
        self.latest_call_code = result.status
        if result.status != 200:
            _LOGGER.error(f"Error getting token {result.status}")
            return
        resultData = await result.json()
        _LOGGER.debug(resultData)

        if resultData['data']:
            self.access_token = resultData['data']['getAuthToken']['access_token']
            self.refresh_token = resultData['data']['getAuthToken']['refresh_token']
            self.token_expiry = datetime.now(
            ) + timedelta(seconds=resultData['data']['getAuthToken']['expires_in'])
            # ID Token

        _LOGGER.debug(f"Response {self.access_token}")

    async def _get_code(self) -> None:
        resumePath = await self._get_resume_path()
        parsed_url = urlparse(resumePath)
        query_params = parse_qs(parsed_url.query)

        # check if code is in query_params
        if query_params.get('code'):
            return query_params.get(('code'))[0]

        # get the resumePath
        if query_params.get('resumePath'):
            resumePath = query_params.get(('resumePath'))[0]

        if resumePath is None:
            return

        params = {
            'client_id': 'polmystar'
        }
        data = {
            'pf.username': self.username,
            'pf.pass': self.password
        }
        result = await self.session.post(
            f"https://polestarid.eu.polestar.com/as/{resumePath}/resume/as/authorization.ping",
            params=params,
            data=data
        )
        self.latest_call_code = result.status
        if result.status != 200:
            _LOGGER.error(f"Error getting code {result.status}")
            return
        # get the realUrl
        url = result.url

        parsed_url = urlparse(result.real_url.raw_path_qs)
        query_params = parse_qs(parsed_url.query)

        if not query_params.get('code'):
            _LOGGER.error(f"Error getting code in {query_params}")
            _LOGGER.warning("Check if username and password are correct")
            return

        code = query_params.get(('code'))[0]

        # sign-in-callback
        result = await self.session.get("https://www.polestar.com/sign-in-callback?code=" + code)
        self.latest_call_code = result.status
        if result.status != 200:
            _LOGGER.error(f"Error getting code callback {result.status}")
            return
        # url encode the code
        result = await self.session.get(url)
        self.latest_call_code = result.status

        return code

    async def _get_resume_path(self):
        # Get Resume Path
        params = {
            "response_type": "code",
            "client_id": "polmystar",
            "redirect_uri": "https://www.polestar.com/sign-in-callback"
        }
        result = await self.session.get("https://polestarid.eu.polestar.com/as/authorization.oauth2", params=params)
        if result.status != 200:
            _LOGGER.error(f"Error getting resume path {result.status}")
            return
        return result.real_url.raw_path_qs
