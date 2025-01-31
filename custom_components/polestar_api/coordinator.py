"""Polestar API for Polestar integration."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import TYPE_CHECKING, Any

import homeassistant.util.dt as dt_util
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from pypolestar.exceptions import PolestarApiException, PolestarAuthException
from pypolestar.models import (
    CarBatteryData,
    CarHealthData,
    CarInformationData,
    CarOdometerData,
)

from .const import DEFAULT_SCAN_INTERVAL

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from pypolestar import PolestarApi

    from .data import PolestarConfigEntry

_LOGGER = logging.getLogger(__name__)


# https://developers.home-assistant.io/docs/integration_fetching_data#coordinated-single-api-poll-for-data-for-all-entities
class PolestarCoordinator(DataUpdateCoordinator):
    """Polestar EV integration."""

    config_entry: PolestarConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        api: PolestarApi,
        config_entry: PolestarConfigEntry,
        vin: str,
    ) -> None:
        """Initialize the Polestar Car."""
        self.config_entry = config_entry
        self.vin = vin.upper()
        super().__init__(
            hass,
            logger=_LOGGER,
            name=f"Polestar {self.get_short_id()}",
            update_interval=DEFAULT_SCAN_INTERVAL,
        )
        self.polestar_api = api

        self.car_information_data: CarInformationData | None = (
            self.polestar_api.get_car_information(self.vin)
        )
        self.car_odometer_data: CarOdometerData | None = None
        self.car_battery_data: CarBatteryData | None = None
        self.car_health_data: CarHealthData | None = None

    @property
    def model(self) -> str:
        return (
            self.car_information_data.model_name if self.car_information_data else None
        ) or "Unknown"

    def get_short_id(self) -> str:
        """Last 4 characters of the VIN"""
        return self.vin[-4:]

    async def _async_update_data(self) -> Any:
        """Update data via library."""

        res = {}
        try:
            await self.polestar_api.update_latest_data(
                vin=self.vin,
                update_telematics=True,
                update_battery=False,
                update_odometer=False,
            )

            if car_telematics_data := self.polestar_api.get_car_telematics(self.vin):
                self.car_odometer_data = car_telematics_data.odometer
                self.car_battery_data = car_telematics_data.battery
                self.car_health_data = car_telematics_data.health

            if not self.car_odometer_data:
                _LOGGER.warning("No odometer information for VIN %s", self.vin)

            if not self.car_battery_data:
                _LOGGER.warning("No battery information for VIN %s", self.vin)

            if not self.car_health_data:
                _LOGGER.debug("No health information for VIN %s", self.vin)

        except PolestarAuthException as exc:
            _LOGGER.error("Authentication failed for VIN %s: %s", self.vin, str(exc))
            res["api_connected"] = False
            raise ConfigEntryAuthFailed(exc) from exc
        except PolestarApiException as exc:
            _LOGGER.error("Update failed for VIN %s: %s", self.vin, str(exc))
            res["api_connected"] = False
            raise UpdateFailed(exc) from exc
        except Exception as exc:
            _LOGGER.error(
                "Unexpected error updating data for VIN %s: %s", self.vin, str(exc)
            )
            res["api_connected"] = False
            raise exc
        else:
            res["api_connected"] = (
                self.get_latest_call_code_data() == 200
                and self.get_latest_call_code_auth() == 200
                and self.polestar_api.auth.is_token_valid()
            )
        finally:
            if token_expire := self.get_token_expiry():
                res["api_token_expires_at"] = dt_util.as_local(token_expire).strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
            else:
                res["api_token_expires_at"] = None
            res["api_status_code_data"] = self.get_latest_call_code_data() or "Error"
            res["api_status_code_auth"] = self.get_latest_call_code_auth() or "Error"
        return res

    def get_token_expiry(self) -> datetime | None:
        """Get the token expiry time."""
        return self.polestar_api.auth.token_expiry

    def get_latest_call_code_data(self) -> int | None:
        """Get the latest call code data API."""
        return self.polestar_api.get_status_code()

    def get_latest_call_code_auth(self) -> int | None:
        """Get the latest call code auth API."""
        return self.polestar_api.auth.get_status_code()
