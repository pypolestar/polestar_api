
import logging

from .pypolestar.polestar import PolestarApi


from .const import (
    CACHE_TIME,
)

from homeassistant.helpers.aiohttp_client import async_get_clientsession

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
        self._session = async_get_clientsession(hass, verify_ssl=False)
        self.polestarApi = PolestarApi(username, password)

        self.vin = None
        self.cache_data = {}
        self.latest_call_code = None
        self.updating = False
        disable_warnings()

    async def init(self):
        await self.polestarApi.init()
        vin = self.get_cache_data('getConsumerCarsV2', 'vin')
        if vin:
            # fill the vin and id in the constructor
            self.vin = vin
            self.id = vin[:8]
            self.name = "Polestar " + vin[-4:]

    def get_cache_data(self, query: str, field_name: str, skip_cache: bool = False):
        return self.polestarApi.get_cache_data(query, field_name, skip_cache)

    async def get_ev_data(self):
        await self.polestarApi.get_ev_data(self.vin)

    def get_latest_data(self, query: str, field_name: str):
        return self.polestarApi.get_latest_data(query, field_name)

    def get_latest_call_code(self):
        return self.polestarApi.latest_call_code
