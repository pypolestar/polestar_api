"""Polestar API for Polestar integration."""

import logging
import re
from datetime import datetime, timedelta

import homeassistant.util.dt as dt_util
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.httpx_client import create_async_httpx_client
from homeassistant.util import Throttle
from pypolestar import PolestarApi

from .const import DEFAULT_SCAN_INTERVAL, DOMAIN as POLESTAR_API_DOMAIN

_LOGGER = logging.getLogger(__name__)


class PolestarCar:
    """Polestar EV integration."""

    def __init__(
        self, api: PolestarApi, vin: str, unique_id: str | None = None
    ) -> None:
        """Initialize the Polestar Car."""
        self.polestar_api = api
        self.vin = vin
        self.unique_id = (
            f"{unique_id}_{self.vin.lower()}" if unique_id else self.vin.lower()
        )
        self.name = "Polestar " + self.get_short_id()
        self.scan_interval = DEFAULT_SCAN_INTERVAL
        self.async_update = Throttle(min_time=self.scan_interval)(self.async_update)
        self.data = {}
        self.update_car_information()

    def get_unique_id(self) -> str:
        """Return unique identifier"""
        return self.unique_id

    def get_short_id(self) -> str:
        """Last 4 characters of the VIN"""
        return self.vin[-4:]

    def get_device_info(self) -> DeviceInfo:
        """Return DeviceInfo for current device"""
        return DeviceInfo(
            identifiers={(POLESTAR_API_DOMAIN, self.get_unique_id())},
            manufacturer="Polestar",
            model=self.data.get("model_name", "Unknown model"),
            name=self.name,
            serial_number=self.vin,
        )

    def update_car_information(self) -> None:
        """Update data with current car information"""

        if data := self.polestar_api.get_car_information(self.vin):
            if data.battery and (match := re.search(r"(\d+) kWh", data.battery)):
                battery_capacity = match.group(1)
            else:
                battery_capacity = None

            if data.torque and (match := re.search(r"(\d+) Nm", data.torque)):
                torque = match.group(1)
            else:
                torque = None

            self.data.update(
                {
                    "vin": self.vin,
                    "internal_vehicle_id": data.internal_vehicle_identifier,
                    "car_image": data.image_url,
                    "registration_number": data.registration_no,
                    "registration_date": data.registration_date,
                    "factory_complete_date": data.factory_complete_date,
                    "model_name": data.model_name,
                    "software_version": data.software_version,
                    "software_version_release": data.software_version_timestamp,
                    "battery_capacity": battery_capacity,
                    "torque": torque,
                }
            )

    def update_battery(self) -> None:
        """Update data with current car battery readings"""

        if data := self.polestar_api.get_car_battery(self.vin):
            if (
                data.battery_charge_level_percentage is not None
                and data.battery_charge_level_percentage != 0
                and data.estimated_distance_to_empty_km is not None
            ):
                estimate_full_charge_range = round(
                    data.estimated_distance_to_empty_km
                    / data.battery_charge_level_percentage
                    * 100,
                    2,
                )
            else:
                estimate_full_charge_range = None

            if data.estimated_charging_time_to_full_minutes:
                timestamp = datetime.now().replace(second=0, microsecond=0) + timedelta(
                    minutes=data.estimated_charging_time_to_full_minutes
                )
                estimated_fully_charged_time = dt_util.as_local(timestamp).strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
            else:
                estimated_fully_charged_time = "Not charging"

            self.data.update(
                {
                    "battery_charge_level": data.battery_charge_level_percentage,
                    "charging_status": data.charging_status,
                    "charger_connection_status": data.charger_connection_status,
                    "charging_power": data.charging_power_watts,
                    "charging_current": data.charging_current_amps,
                    "average_energy_consumption_kwh_per_100": data.average_energy_consumption_kwh_per_100km,
                    "estimate_range": data.estimated_distance_to_empty_km,
                    "estimate_full_charge_range": estimate_full_charge_range,
                    "estimated_charging_time_minutes_to_target_distance": data.estimated_charging_time_minutes_to_target_distance,
                    "estimated_charging_time_to_full": data.estimated_charging_time_to_full_minutes,
                    "estimated_fully_charged_time": estimated_fully_charged_time,
                    "last_updated_battery_data": data.event_updated_timestamp,
                }
            )

    def update_odometer(self) -> None:
        """Update data with current car odometer readings"""

        if data := self.polestar_api.get_car_odometer(self.vin):
            self.data.update(
                {
                    "current_odometer": data.odometer_meters,
                    "average_speed": data.average_speed_km_per_hour,
                    "current_trip_meter_automatic": data.trip_meter_automatic_km,
                    "current_trip_meter_manual": data.trip_meter_manual_km,
                    "last_updated_odometer_data": data.event_updated_timestamp,
                }
            )

    async def async_update(self) -> None:
        """Update data from Polestar."""

        try:
            await self.polestar_api.update_latest_data(self.vin)
            self.update_odometer()
            self.update_battery()
        except Exception as e:
            _LOGGER.error(f"Failed to update data for VIN {self.vin}: {e}")
            self.data["api_connected"] = False
        else:
            _LOGGER.debug(f"Updated data for VIN {self.vin}")
            self.data["api_connected"] = (
                self.get_latest_call_code_data() == 200
                and self.get_latest_call_code_auth() == 200
                and self.polestar_api.auth.is_token_valid()
            )

        if token_expire := self.get_token_expiry():
            self.data["api_token_expires_at"] = dt_util.as_local(token_expire).strftime(
                "%Y-%m-%d %H:%M:%S"
            )
        else:
            self.data["api_token_expires_at"] = None

        self.data["api_status_code_data"] = self.get_latest_call_code_data() or "Error"
        self.data["api_status_code_auth"] = self.get_latest_call_code_auth() or "Error"

    def get_token_expiry(self) -> datetime | None:
        """Get the token expiry time."""
        return self.polestar_api.auth.token_expiry

    def get_latest_call_code_data(self) -> int | None:
        """Get the latest call code data API."""
        return self.polestar_api.get_status_code()

    def get_latest_call_code_auth(self) -> int | None:
        """Get the latest call code auth API."""
        return self.polestar_api.auth.get_status_code()


class PolestarCoordinator:
    """Polestar EV integration."""

    def __init__(
        self,
        hass: HomeAssistant,
        username: str,
        password: str,
        vin: str | None,
        unique_id: str | None = None,
    ) -> None:
        """Initialize the Polestar API."""
        if vin:
            _LOGGER.debug("Configure Polestar API client for car with VIN %s", vin)
        else:
            _LOGGER.debug("Configure Polestar API client for all cars")
        self.unique_id = unique_id
        self.username = username
        self.polestar_api = PolestarApi(
            username=username,
            password=password,
            client_session=create_async_httpx_client(hass),
            vins=[vin] if vin else None,
            unique_id=self.unique_id,
        )

    async def async_init(self):
        """Initialize the Polestar API."""
        await self.polestar_api.async_init()

    def get_cars(self) -> list[PolestarCar]:
        return [
            PolestarCar(api=self.polestar_api, vin=vin, unique_id=self.unique_id)
            for vin in self.polestar_api.get_available_vins()
        ]
