from datetime import timedelta
import json
import logging

from homeassistant.helpers.aiohttp_client import async_get_clientsession

from urllib3 import disable_warnings

from homeassistant.core import HomeAssistant
from homeassistant.util import Throttle
from .polestar_api import PolestarApi


POST_HEADER_JSON = {"Content-Type": "application/json"}

_LOGGER = logging.getLogger(__name__)


class Polestar:

    QUERY_PAYLOAD = '{"query": "{ me { homes { electricVehicles {id name shortName lastSeen lastSeenText isAlive hasNoSmartChargingCapability imgUrl schedule {isEnabled isSuspended localTimeTo minBatteryLevel} batteryText chargingText consumptionText consumptionUnitText energyCostUnitText chargeRightAwayButton chargeRightAwayAlert {imgUrl title description okText cancelText}backgroundStyle energyDealCallToAction{text url redirectUrlStartsWith link action enabled} settingsScreen{settings {key value valueType valueIsArray isReadOnly inputOptions{type title description pickerOptions {values postFix} rangeOptions{max min step defaultValue displayText displayTextPlural} selectOptions {value title description imgUrl iconName isRecommendedOption} textFieldOptions{imgUrl format placeholder} timeOptions{doNotSetATimeText}}} settingsLayout{uid type title description valueText imgUrl iconName isUpdated isEnabled callToAction {text url redirectUrlStartsWith link action enabled} childItems{uid type title description valueText imgUrl iconName isUpdated isEnabled callToAction {text url redirectUrlStartsWith link action enabled} settingKey settingKeyForIsHidden} settingKey settingKeyForIsHidden}} settingsButtonText settingsButton  {text url redirectUrlStartsWith link action enabled}enterPincode message {id title description style iconName iconSrc callToAction {text url redirectUrlStartsWith link action enabled} dismissButtonText} scheduleSuspendedText faqUrl battery { percent percentColor isCharging chargeLimit}}}}}"}'

    def __init__(self,
                 hass: HomeAssistant,
                 raw_data: str,
                 polestar_api: PolestarApi) -> None:

        ev_id = raw_data.get("id").replace("-", "")[:8]
        ev_name = raw_data.get("name")
        self.id = ev_id
        self.name = ev_name
        self.raw_data = raw_data
        self.polestar_api = polestar_api
        disable_warnings()

    async def init(self) -> None:
        self.id = "polestar{}".format(self.name)
        if self.name is None:
            self.name = f"{self.info.identity} ({self.host})"

    @property
    def status(self) -> str:
        return self._status

    @Throttle(timedelta(seconds=10))
    async def async_update(self) -> None:
        self.raw_data = await self.polestar_api.get_ev_data()
