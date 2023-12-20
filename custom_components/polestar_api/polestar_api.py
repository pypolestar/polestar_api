from datetime import datetime, timedelta
import json
import logging

from urllib.parse import parse_qs, urlparse

from .const import (
    CACHE_TIME,
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
                 password: str
                 ) -> None:
        self.id = None
        self.name = "Polestar "
        self._session = async_get_clientsession(hass, verify_ssl=False)
        self.username = username
        self.password = password
        self.access_token = None
        self.token_type = None
        self.refresh_token = None
        self.vin = None
        self.cache_data = {}
        self.latest_call_code = None
        self.updating = False
        disable_warnings()

    async def init(self):
        await self.get_token()
        if self.access_token is None:
            return
        result = await self.get_vehicle_data()

        # check if there are cars in the account
        if result['data']['getConsumerCarsV2'] is None or len(result['data']['getConsumerCarsV2']) == 0:
            _LOGGER.exception("No cars found in account")
            # throw new exception
            raise Exception("No cars found in account")

        self.cache_data['getConsumerCarsV2'] = {
            'data': result['data']['getConsumerCarsV2'][0], 'timestamp': datetime.now()}

        # fill the vin and id in the constructor
        self.vin = result['data']['getConsumerCarsV2'][0]['vin']
        self.id = self.vin[:8]
        self.name = "Polestar " + self.vin[-4:]

    async def _get_resume_path(self):
        # Get Resume Path
        params = {
            "response_type": "code",
            "client_id": "polmystar",
            "redirect_uri": "https://www.polestar.com/sign-in-callback"
        }
        result = await self._session.get("https://polestarid.eu.polestar.com/as/authorization.oauth2", params=params)
        if result.status != 200:
            _LOGGER.error(f"Error getting resume path {result.status}")
            return
        return result.real_url.raw_path_qs

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
        result = await self._session.post(
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
        result = await self._session.get("https://www.polestar.com/sign-in-callback?code=" + code)
        self.latest_call_code = result.status
        if result.status != 200:
            _LOGGER.error(f"Error getting code callback {result.status}")
            return
        # url encode the code
        result = await self._session.get(url)
        self.latest_call_code = result.status

        return code

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
        result = await self._session.get("https://pc-api.polestar.com/eu-north-1/auth/", params=params, headers=headers)
        self.latest_call_code = result.status
        if result.status != 200:
            _LOGGER.error(f"Error getting token {result.status}")
            return
        resultData = await result.json()
        _LOGGER.debug(resultData)

        self.access_token = resultData['data']['getAuthToken']['access_token']
        self.refresh_token = resultData['data']['getAuthToken']['refresh_token']
        # ID Token

        _LOGGER.debug(f"Response {self.access_token}")

    def get_latest_data(self, query: str, field_name: str) -> dict or bool or None:
        if self.cache_data and self.cache_data[query]:
            data = self.cache_data[query]['data']
            if data is None:
                return False
            return self._get_field_name_value(field_name, data)

    def _get_field_name_value(self, field_name: str, data: dict) -> str or bool or None:
        if field_name is None:
            return None

        if data is None:
            return None

        if '/' in field_name:
            field_name = field_name.split('/')
        if data:
            if isinstance(field_name, list):
                for key in field_name:
                    if data.get(key):
                        data = data[key]
                    else:
                        return None
                return data
            return data[field_name]
        return None

    def get_cache_data(self, query: str, field_name: str, skip_cache: bool = False):
        if query is None:
            return None

        if self.cache_data and self.cache_data.get(query):
            if skip_cache is False:
                if self.cache_data[query]['timestamp'] + timedelta(seconds=CACHE_TIME) > datetime.now():
                    data = self.cache_data[query]['data']
                    if data is None:
                        return None
                    return self._get_field_name_value(field_name, data)
            else:
                data = self.cache_data[query]['data']
                if data is None:
                    return None
                return self._get_field_name_value(field_name, data)
        return None

    async def getOdometerData(self):
        result = await self.get_odo_data()
        # put result in cache
        self.cache_data['getOdometerData'] = {
            'data': result['data']['getOdometerData'], 'timestamp': datetime.now()}

    async def getBatteryData(self):
        result = await self.get_battery_data()
        # put result in cache
        self.cache_data['getBatteryData'] = {
            'data': result['data']['getBatteryData'], 'timestamp': datetime.now()}

    async def get_ev_data(self):
        if self.updating is True:
            return
        self.updating = True
        await self.getOdometerData()
        await self.getBatteryData()
        self.updating = False

    async def get_graph_ql(self, params: dict):
        headers = {
            "Content-Type": "application/json",
            "authorization": "Bearer " + self.access_token
        }

        result = await self._session.get("https://pc-api.polestar.com/eu-north-1/my-star/", params=params, headers=headers)
        self.latest_call_code = result.status
        resultData = await result.json()

        # if auth error, get new token
        if resultData.get('errors'):
            if resultData['errors'][0]['message'] == 'User not authenticated':
                await self.get_token()
                resultData = await self.get_graph_ql(params)
            else:
                # log the error
                _LOGGER.warning(resultData.get('errors'))
                self.latest_call_code = 500  # set internal error
        _LOGGER.debug(resultData)
        return resultData

    async def get_odo_data(self):
        # get Odo Data
        params = {
            "query": "query GetOdometerData($vin: String!) { getOdometerData(vin: $vin) { averageSpeedKmPerHour eventUpdatedTimestamp { iso unix __typename } odometerMeters tripMeterAutomaticKm tripMeterManualKm __typename }}",
            "operationName": "GetOdometerData",
            "variables": "{\"vin\":\"" + self.vin + "\"}"
        }
        return await self.get_graph_ql(params)

    async def get_battery_data(self):
        # get Battery Data
        params = {
            "query": "query GetBatteryData($vin: String!) {  getBatteryData(vin: $vin) {    averageEnergyConsumptionKwhPer100Km    batteryChargeLevelPercentage    chargerConnectionStatus    chargingCurrentAmps    chargingPowerWatts    chargingStatus    estimatedChargingTimeMinutesToTargetDistance    estimatedChargingTimeToFullMinutes    estimatedDistanceToEmptyKm    estimatedDistanceToEmptyMiles    eventUpdatedTimestamp {      iso      unix      __typename    }    __typename  }}",
            "operationName": "GetBatteryData",
            "variables": "{\"vin\":\"" + self.vin + "\"}"
        }
        return await self.get_graph_ql(params)

    async def get_vehicle_data(self):
        # get Vehicle Data
        params = {
            "query": "query getCars {  getConsumerCarsV2 {    vin    internalVehicleIdentifier    modelYear    content {      model {        code        name        __typename      }      images {        studio {          url          angles          __typename        }        __typename      }      __typename    }    hasPerformancePackage    registrationNo    deliveryDate    currentPlannedDeliveryDate    __typename  }}",
            "operationName": "getCars",
            "variables": "{}"
        }
        return await self.get_graph_ql(params)
