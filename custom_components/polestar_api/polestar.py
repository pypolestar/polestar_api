"""Polestar API for Polestar integration."""
from datetime import datetime, timedelta
import logging

import httpx
from urllib3 import disable_warnings

from homeassistant.core import HomeAssistant
from homeassistant.util.unit_system import METRIC_SYSTEM, US_CUSTOMARY_SYSTEM, UnitSystem

from .pypolestar.exception import PolestarApiException, PolestarAuthException
from .pypolestar.polestar import PolestarApi

POST_HEADER_JSON = {"Content-Type": "application/json"}

_LOGGER = logging.getLogger(__name__)


class Polestar:
    def __init__(self,
                 hass: HomeAssistant,
                 username: str,
                 password: str
                 ) -> None:
        self.id = None
        self.name = "Polestar "
        self.polestarApi = PolestarApi(username, password)
        self.vin = None
        self.unit_system = METRIC_SYSTEM
        disable_warnings()

    async def init(self):
        await self.polestarApi.init()
        vin = self.get_value('getConsumerCarsV2', 'vin', True)
        if vin:
            # fill the vin and id in the constructor
            self.vin = vin
            self.id = vin[:8]
            self.name = "Polestar " + vin[-4:]

    def get_token_expiry(self):
        return self.polestarApi.auth.token_expiry

    def get_latest_data(self, query: str, field_name: str):
        return self.polestarApi.get_latest_data(query, field_name)

    def get_latest_call_code(self):
        # if AUTH code last code is not 200 then we return that error code,
        # otherwise just give the call_code in API
        if self.polestarApi.auth.latest_call_code != 200:
            return self.polestarApi.auth.latest_call_code
        return self.polestarApi.latest_call_code

    async def async_update(self) -> None:
        try:
            await self.polestarApi.get_ev_data(self.vin)
        except PolestarApiException as e:
            _LOGGER.warning("API Exception on update data %s", str(e))
            self.polestarApi.next_update = datetime.now() + timedelta(seconds=5)
        except PolestarAuthException as e:
            _LOGGER.warning("Auth Exception on update data %s", str(e))
            self.polestarApi.next_update = datetime.now() + timedelta(seconds=5)
        except httpx.ConnectTimeout as e:
            _LOGGER.warning("Connection Timeout on update data %s", str(e))
            self.polestarApi.next_update = datetime.now() + timedelta(seconds=15)
        except httpx.ConnectError as e:
            _LOGGER.warning("Connection Error on update data %s", str(e))
            self.polestarApi.next_update = datetime.now() + timedelta(seconds=15)
        except httpx.ReadTimeout as e:
            _LOGGER.warning("Read Timeout on update data %s", str(e))
            self.polestarApi.next_update = datetime.now() + timedelta(seconds=15)
        except Exception as e:
            _LOGGER.error("Unexpected Error on update data %s", str(e))
            self.polestarApi.next_update = datetime.now() + timedelta(seconds=60)

    def set_config_unit(self, unit:UnitSystem):
        self.unit_system = unit

    def get_config_unit(self):
        return self.unit_system

    def get_value(self, query: str, field_name: str, skip_cache: bool = False):
        data = self.polestarApi.get_cache_data(query, field_name, skip_cache)
        if data is None:
            return
        return data
