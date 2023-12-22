import logging
import httpx

from datetime import datetime, timedelta
from .auth import PolestarAuth
from .const import CACHE_TIME, BATTERY_DATA, CAR_INFO_DATA, ODO_METER_DATA

_LOGGER = logging.getLogger(__name__)


class PolestarApi:

    def __init__(self, username: str, password: str) -> None:
        self.auth = PolestarAuth(username, password)
        self.updating = False
        self.cache_data = {}
        self.latest_call_code = None
        self._client_session = httpx.AsyncClient()

    async def init(self):
        await self.auth.get_token()

        if self.auth.access_token is None:
            return

        result = await self.get_vehicle_data()

        # check if there are cars in the account
        if result['data'][CAR_INFO_DATA] is None or len(result['data'][CAR_INFO_DATA]) == 0:
            _LOGGER.exception("No cars found in account")
            # throw new exception
            raise Exception("No cars found in account")

        self.cache_data[CAR_INFO_DATA] = {
            'data': result['data'][CAR_INFO_DATA][0], 'timestamp': datetime.now()}

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

    async def getOdometerData(self, vin: str):
        result = await self.get_odo_data(vin)

        if result and result['data']:
            # put result in cache
            self.cache_data[ODO_METER_DATA] = {
                'data': result['data'][ODO_METER_DATA], 'timestamp': datetime.now()}

    async def getBatteryData(self, vin: str):
        result = await self.get_battery_data(vin)

        if result and result['data']:
            # put result in cache
            self.cache_data[BATTERY_DATA] = {
                'data': result['data'][BATTERY_DATA], 'timestamp': datetime.now()}

    async def get_vehicle_data(self):
        result = await self.get_vehicle_data()
        if result and result['data']:
            # check if there are cars in the account
            if result['data'][CAR_INFO_DATA] is None or len(result['data'][CAR_INFO_DATA]) == 0:
                _LOGGER.exception("No cars found in account")
                # throw new exception
                raise Exception("No cars found in account")

            self.cache_data[CAR_INFO_DATA] = {
                'data': result['data'][CAR_INFO_DATA][0], 'timestamp': datetime.now()}

    async def get_ev_data(self, vin: str):
        if self.updating is True:
            return
        self.updating = True
        await self.getOdometerData(vin)
        await self.getBatteryData(vin)
        self.updating = False

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

    async def get_graph_ql(self, params: dict):
        headers = {
            "Content-Type": "application/json",
            "authorization": "Bearer " + self.auth.access_token
        }

        result = await self._client_session.get("https://pc-api.polestar.com/eu-north-1/my-star/", params=params, headers=headers)
        self.latest_call_code = result.status_code
        resultData = result.json()

        # if auth error, get new token
        if resultData.get('errors'):
            if resultData['errors'][0]['message'] == 'User not authenticated':
                await self.auth.get_token()
                resultData = await self.get_graph_ql(params)
            else:
                # log the error
                _LOGGER.warning(resultData.get('errors'))
                self.latest_call_code = 500  # set internal error
                return None
        _LOGGER.debug(resultData)
        return resultData

    async def get_battery_data(self, vin: str):
        # get Battery Data
        params = {
            "query": "query GetBatteryData($vin: String!) {  getBatteryData(vin: $vin) {    averageEnergyConsumptionKwhPer100Km    batteryChargeLevelPercentage    chargerConnectionStatus    chargingCurrentAmps    chargingPowerWatts    chargingStatus    estimatedChargingTimeMinutesToTargetDistance    estimatedChargingTimeToFullMinutes    estimatedDistanceToEmptyKm    estimatedDistanceToEmptyMiles    eventUpdatedTimestamp {      iso      unix      __typename    }    __typename  }}",
            "operationName": "GetBatteryData",
            "variables": "{\"vin\":\"" + vin + "\"}"
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

    async def get_odo_data(self, vin: str):
        # get Odo Data
        params = {
            "query": "query GetOdometerData($vin: String!) { getOdometerData(vin: $vin) { averageSpeedKmPerHour eventUpdatedTimestamp { iso unix __typename } odometerMeters tripMeterAutomaticKm tripMeterManualKm __typename }}",
            "operationName": "GetOdometerData",
            "variables": "{\"vin\":\"" + vin + "\"}"
        }
        return await self.get_graph_ql(params)
