"""Polestar API for Polestar integration."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import TYPE_CHECKING, Any

import homeassistant.util.dt as dt_util
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from pypolestar.exceptions import PolestarApiException, PolestarAuthException

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
        self.unique_id = self.vin
        self.polestar_api = api
        self.car_information = self.get_car_information()
        self.model = (
            self.car_information["model_name"] if self.car_information else "Unknown"
        )

    def get_short_id(self) -> str:
        """Last 4 characters of the VIN"""
        return self.vin[-4:]

    def get_car_information(self) -> dict[str, Any]:
        """Get current car information"""

        if data := self.polestar_api.get_car_information(self.vin):
            return {
                "vin": self.vin,
                "internal_vehicle_id": data.internal_vehicle_identifier,
                "car_image": data.image_url,
                "registration_number": data.registration_no,
                "registration_date": data.registration_date,
                "factory_complete_date": data.factory_complete_date,
                "model_name": data.model_name,
                "software_version": data.software_version,
                "software_version_release": data.software_version_timestamp,
                "battery_capacity": data.battery_information.capacity
                if data.battery_information
                else None,
                "torque": data.torque_nm,
            }
        else:
            _LOGGER.warning("No car information for VIN %s", self.vin)
            return {}

    def get_car_battery(self) -> dict[str, Any]:
        """Get current car battery readings"""

        if data := self.polestar_api.get_car_battery(self.vin):
            estimated_fully_charged_time = (
                dt_util.as_local(data.estimated_fully_charged).strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
                if data.estimated_fully_charged
                else None
            )

            return {
                "battery_charge_level": data.battery_charge_level_percentage,
                "charging_status": data.charging_status,
                "charger_connection_status": data.charger_connection_status,
                "charging_power": data.charging_power_watts,
                "charging_current": data.charging_current_amps,
                "average_energy_consumption": data.average_energy_consumption_kwh_per_100km,
                "estimated_range": data.estimated_distance_to_empty_km,
                "estimated_full_charge_range": data.estimated_full_charge_range_km,
                "estimated_charging_time_to_target_distance": data.estimated_charging_time_minutes_to_target_distance,
                "estimated_charging_time_to_full": data.estimated_charging_time_to_full_minutes,
                "estimated_fully_charged_time": estimated_fully_charged_time,
                "last_updated_battery_data": data.event_updated_timestamp,
            }
        else:
            _LOGGER.warning("No battery information for VIN %s", self.vin)
            return {}

    def get_car_odometer(self) -> dict[str, Any]:
        """Get current car odometer readings"""

        if data := self.polestar_api.get_car_odometer(self.vin):
            return {
                "current_odometer": data.odometer_meters,
                "average_speed": data.average_speed_km_per_hour,
                "current_trip_meter_automatic": data.trip_meter_automatic_km,
                "current_trip_meter_manual": data.trip_meter_manual_km,
                "last_updated_odometer_data": data.event_updated_timestamp,
            }
        else:
            _LOGGER.warning("No odometer information for VIN %s", self.vin)
            return {}

    async def _async_update_data(self) -> Any:
        """Update data via library."""

        res = self.car_information.copy()
        try:
            await self.polestar_api.update_latest_data(self.vin)
            res.update(self.get_car_odometer())
            res.update(self.get_car_battery())
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
