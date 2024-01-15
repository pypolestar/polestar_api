"""Asynchronous Python client for the Polestar API."""""
from datetime import datetime, timedelta
import logging

import httpx

from .auth import PolestarAuth
from .const import BATTERY_DATA, CACHE_TIME, CAR_INFO_DATA, ODO_METER_DATA
from .exception import (
    PolestarApiException,
    PolestarAuthException,
    PolestarNoDataException,
    PolestarNotAuthorizedException,
)

_LOGGER = logging.getLogger(__name__)


class PolestarApi:
    """Main class for handling connections with the Polestar API."""

    def __init__(self, username: str, password: str) -> None:
        """Initialize the Polestar API."""
        self.auth = PolestarAuth(username, password)
        self.updating = False
        self.cache_data = {}
        self.latest_call_code = None
        self._client_session = httpx.AsyncClient()
        self.next_update = None


    async def init(self):
        """Initialize the Polestar API."""
        try:
            await self.auth.get_token()

            if self.auth.access_token is None:
                return

            await self._get_vehicle_data()

        except PolestarAuthException as e:
            _LOGGER.exception("Auth Exception: %s", str(e))

    def get_latest_data(self, query: str, field_name: str) -> dict or bool or None:
        """Get the latest data from the Polestar API."""
        if self.cache_data and self.cache_data[query]:
            data = self.cache_data[query]['data']
            if data is None:
                return False
            return self._get_field_name_value(field_name, data)

    def _get_field_name_value(self, field_name: str, data: dict) -> str or bool or None:
        if field_name is None or data is None:
            return None

        if '/' in field_name:
            field_names = field_name.split('/')
            for key in field_names:
                if isinstance(data, dict) and key in data:
                    data = data[key]
                else:
                    return None
            return data

        if isinstance(data, dict) and field_name in data:
            return data[field_name]

        return None

    async def _get_odometer_data(self, vin: str):
        """" Get the latest odometer data from the Polestar API."""
        params = {
            "query": "query GetOdometerData($vin: String!) { getOdometerData(vin: $vin) { averageSpeedKmPerHour eventUpdatedTimestamp { iso unix __typename } odometerMeters tripMeterAutomaticKm tripMeterManualKm __typename }}",
            "operationName": "GetOdometerData",
            "variables": "{\"vin\":\"" + vin + "\"}"
        }
        result = await self.get_graph_ql(params)

        if result and result['data']:
            # put result in cache
            self.cache_data[ODO_METER_DATA] = {
                'data': result['data'][ODO_METER_DATA], 'timestamp': datetime.now()}

    async def _get_battery_data(self, vin: str):
        params = {
            "query": "query GetBatteryData($vin: String!) {  getBatteryData(vin: $vin) {    averageEnergyConsumptionKwhPer100Km    batteryChargeLevelPercentage    chargerConnectionStatus    chargingCurrentAmps    chargingPowerWatts    chargingStatus    estimatedChargingTimeMinutesToTargetDistance    estimatedChargingTimeToFullMinutes    estimatedDistanceToEmptyKm    estimatedDistanceToEmptyMiles    eventUpdatedTimestamp {      iso      unix      __typename    }    __typename  }}",
            "operationName": "GetBatteryData",
            "variables": "{\"vin\":\"" + vin + "\"}"
        }

        result = await self.get_graph_ql(params)

        if result and result['data']:
            # put result in cache
            self.cache_data[BATTERY_DATA] = {
                'data': result['data'][BATTERY_DATA], 'timestamp': datetime.now()}

    async def _get_vehicle_data(self):
        """" Get the latest vehicle data from the Polestar API."""
        # get Vehicle Data
        params = {
            "query": "query GetConsumerCarsV2($locale: String) {   getConsumerCarsV2(locale: $locale) {     vin     internalVehicleIdentifier     registrationNo     market     hasPerformancePackage     software {       performanceOptimization {         value         __typename       }       __typename     }     content {       exterior {         name         __typename       }       interior {         name         __typename       }       wheels {         name         __typename       }       dimensions {         wheelbase {           label           value           __typename         }         groundClearanceWithPerformance {           value           label           __typename         }         groundClearanceWithoutPerformance {           value           label           __typename         }         dimensions {           label           value           __typename         }         __typename       }       specification {         totalHp         torque         totalKw         battery         trunkCapacity {           value           label           __typename         }         __typename       }       motor {         name         __typename       }       performanceOptimizationSpecification {         power {           value           unit           __typename         }         torqueMax {           value           unit           __typename         }         acceleration {           value           unit           description           __typename         }         __typename       }       __typename     }     modelYear     numberOfDoors     features {       code       description       name       type       __typename     }     fuelType     originalMarket  energy {elecRange  elecRangeUnit   elecEnergyConsumption   elecEnergyUnit  weightedCombinedCO2 weightedCombinedCO2Unit weightedCombinedFuelConsumption weightedCombinedFuelConsumptionUnit }  __typename   } }",
            "operationName": "GetConsumerCarsV2",
            "variables": "{}"
        }

        result = await self.get_graph_ql(params)
        if result and result['data']:
            # check if there are cars in the account
            if result['data'][CAR_INFO_DATA] is None or len(result['data'][CAR_INFO_DATA]) == 0:
                _LOGGER.exception("No cars found in account")
                # throw new exception
                raise PolestarNoDataException("No cars found in account")

            self.cache_data[CAR_INFO_DATA] = {
                'data': result['data'][CAR_INFO_DATA][0], 'timestamp': datetime.now()}

    async def get_ev_data(self, vin: str):
        """Get the latest ev data from the Polestar API."""
        if self.updating:
            return

        if self.next_update is not None and self.next_update > datetime.now():
            _LOGGER.debug("Skipping update, next update at %s", self.next_update)
            return

        self.updating = True

        try:
            if self.auth.token_expiry is None:
                raise PolestarAuthException("No token expiry found", 500)
            if (self.auth.token_expiry - datetime.now()).total_seconds() < 300:
                await self.auth.get_token(refresh=True)
        except PolestarAuthException as e:
            self.latest_call_code = 500
            _LOGGER.warning("Auth Exception: %s", str(e))
            self.updating = False
            return

        async def call_api(func):
            try:
                await func()
            except PolestarNotAuthorizedException:
                await self.auth.get_token()
            except PolestarApiException as e:
                self.latest_call_code = 500
                _LOGGER.warning('Failed to get %s data %s',
                                func.__name__, str(e))

        await call_api(lambda: self._get_odometer_data(vin))
        await call_api(lambda: self._get_battery_data(vin))

        self.updating = False
        self.next_update = datetime.now() + timedelta(seconds=5)

    def get_cache_data(self, query: str, field_name: str, skip_cache: bool = False):
        """" Get the latest data from the cache."""
        if query is None:
            return None

        if self.cache_data and self.cache_data.get(query):
            cache_entry = self.cache_data[query]
            data = cache_entry['data']
            if data is not None:
                if skip_cache is True or cache_entry['timestamp'] + timedelta(seconds=CACHE_TIME) > datetime.now():
                    return self._get_field_name_value(field_name, data)
        return None

    async def get_graph_ql(self, params: dict):
        """Get the latest data from the Polestar API."""
        headers = {
            "Content-Type": "application/json",
            "authorization": f"Bearer {self.auth.access_token}"
        }

        url = "https://pc-api.polestar.com/eu-north-1/my-star/"
        result = await self._client_session.get(url, params=params, headers=headers)
        self.latest_call_code = result.status_code

        if result.status_code == 401:
            raise PolestarNotAuthorizedException("Unauthorized Exception")

        if result.status_code != 200:
            raise PolestarApiException(f"Get GraphQL error: {result.text}")

        resultData = result.json()
        if resultData.get('errors'):
            self.latest_call_code = 500
            error_message = resultData['errors'][0]['message']
            if error_message == "User not authenticated":
                raise PolestarNotAuthorizedException("Unauthorized Exception")
            _LOGGER.error(resultData.get('errors'))
            raise PolestarApiException(error_message)

        _LOGGER.debug(resultData)
        return resultData
