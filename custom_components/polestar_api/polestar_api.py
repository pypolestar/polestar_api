from datetime import datetime, timedelta
import json
import logging
from .const import (
    ACCESS_TOKEN_MANAGER_ID,
    AUTHORIZATION,
    CACHE_TIME,
    GRANT_TYPE,
    HEADER_AUTHORIZATION,
    HEADER_VCC_API_KEY
)

from homeassistant.helpers.aiohttp_client import async_get_clientsession

from urllib3 import disable_warnings

from homeassistant.core import HomeAssistant


POST_HEADER_JSON = {"Content-Type": "application/json"}

_LOGGER = logging.getLogger(__name__)


class PolestarApi:
    def __init__(self,
                 hass: HomeAssistant,
                 username: str,
                 password: str,
                 vin: str,
                 vcc_api_key: str,
                 ) -> None:
        self.id = vin[:8]
        self.name = "Polestar " + vin[-4:]
        self._session = async_get_clientsession(hass, verify_ssl=False)
        self.username = username
        self.password = password
        self.access_token = None
        self.token_type = None
        self.refresh_token = None
        self.vin = vin
        self.vcc_api_key = vcc_api_key
        self.cache_data = None
        disable_warnings()

    async def init(self):
        await self.get_token()

    async def get_token(self) -> None:
        response = await self._session.post(
            url='https://volvoid.eu.volvocars.com/as/token.oauth2',
            data={
                'username': self.username,
                'password': self.password,
                'grant_type': GRANT_TYPE,
                'access_token_manager_id': ACCESS_TOKEN_MANAGER_ID,
                'scope': 'openid email profile care_by_volvo:financial_information:invoice:read care_by_volvo:financial_information:payment_method care_by_volvo:subscription:read customer:attributes customer:attributes:write order:attributes vehicle:attributes tsp_customer_api:all conve:brake_status conve:climatization_start_stop conve:command_accessibility conve:commands conve:diagnostics_engine_status conve:diagnostics_workshop conve:doors_status conve:engine_status conve:environment conve:fuel_status conve:honk_flash conve:lock conve:lock_status conve:navigation conve:odometer_status conve:trip_statistics conve:tyre_status conve:unlock conve:vehicle_relation conve:warnings conve:windows_status energy:battery_charge_level energy:charging_connection_status energy:charging_system_status energy:electric_range energy:estimated_charging_time energy:recharge_status'
            },
            headers={
                HEADER_AUTHORIZATION: AUTHORIZATION,
                'content-type': 'application/x-www-form-urlencoded',
                'user-agent': 'okhttp/4.10.0'
            },
        )
        _LOGGER.debug(f"Response {response}")
        if response.status != 200:
            _LOGGER.info("Info API not available")
            return
        resp = await response.json(content_type=None)
        self.access_token = resp['access_token']
        self.refresh_token = resp['refresh_token']
        self.token_type = resp['token_type']

        _LOGGER.debug(f"Response {self.access_token}")

    def get_cache_data(self, path: str, reponse_path: str = None) -> dict or bool or None:
        # replace the string {vin} with the actual vin
        path = path.replace('{vin}', self.vin)

        if self.cache_data and self.cache_data[path]:
            if self.cache_data[path]['timestamp'] > datetime.now() - timedelta(seconds=CACHE_TIME):
                data = self.cache_data[path]['data']
                if data is None:
                    return False
                if reponse_path:
                    for key in reponse_path.split('.'):
                        data = data[key]
                return data

    async def get_data(self, path: str, reponse_path: str = None) -> dict or bool or None:
        path = path.replace('{vin}', self.vin)

        cache_data = self.get_cache_data(path, reponse_path)
        # if false, then we are fetching data just return
        if cache_data is False:
            return
        if cache_data:
            _LOGGER.debug("Using cached data")
            return cache_data

        # put as fast possible something in the cache otherwise we get a lot of requests
        if not self.cache_data:
            self.cache_data = {}
        self.cache_data[path] = {'data': None, 'timestamp': datetime.now()}

        url = 'https://api.volvocars.com/energy/v1/vehicles/' + path
        headers = {
            HEADER_AUTHORIZATION: f'{self.token_type} {self.access_token}',
            HEADER_VCC_API_KEY: self.vcc_api_key
        }

        response = await self._session.get(
            url=url,
            headers=headers
        )
        _LOGGER.debug(f"Response {response}")
        if response.status == 401:
            await self.get_token()
            return
        if response.status != 200:
            _LOGGER.debug("Info API not available")
            return
        resp = await response.json(content_type=None)

        _LOGGER.debug(f"Response {resp}")

        data = resp['data']

        # add cache_data[path]
        self.cache_data[path] = {'data': data, 'timestamp': datetime.now()}

        if reponse_path:
            for key in reponse_path.split('.'):
                data = data[key]

        return data
