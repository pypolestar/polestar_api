
from datetime import timedelta
import logging

from .pypolestar.polestar import PolestarApi

from urllib3 import disable_warnings

from homeassistant.core import HomeAssistant

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
        disable_warnings()

    async def init(self):
        await self.polestarApi.init()
        vin = self.get_value('getConsumerCarsV2', 'vin', True)
        if vin:
            # fill the vin and id in the constructor
            self.vin = vin
            self.id = vin[:8]
            self.name = "Polestar " + vin[-4:]

    def get_latest_data(self, query: str, field_name: str):
        return self.polestarApi.get_latest_data(query, field_name)

    def get_latest_call_code(self):
        # if AUTH code last code is not 200 then we return that error code,
        # otherwise just give the call_code in API
        if self.polestarApi.auth.latest_call_code != 200:
            return self.polestarApi.auth.latest_call_code
        return self.polestarApi.latest_call_code

    async def async_update(self) -> None:
        await self.polestarApi.get_ev_data(self.vin)

    def get_value(self, query: str, field_name: str, skip_cache: bool = False):
        data = self.polestarApi.get_cache_data(query, field_name, skip_cache)
        if data is None:
            return
        return data
