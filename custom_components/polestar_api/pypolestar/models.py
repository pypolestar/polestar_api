from dataclasses import dataclass
from datetime import date, datetime, timezone
from enum import StrEnum
from typing import Self

from .utils import (
    GqlDict,
    get_field_name_date,
    get_field_name_datetime,
    get_field_name_float,
    get_field_name_int,
    get_field_name_str,
)


class ChargingConnectionStatus(StrEnum):
    CHARGER_CONNECTION_STATUS_CONNECTED = "Connected"
    CHARGER_CONNECTION_STATUS_DISCONNECTED = "Disconnected"
    CHARGER_CONNECTION_STATUS_FAULT = "Fault"
    CHARGER_CONNECTION_STATUS_UNSPECIFIED = "Unspecified"


class ChargingStatus(StrEnum):
    CHARGING_STATUS_DONE = "Done"
    CHARGING_STATUS_IDLE = "Idle"
    CHARGING_STATUS_CHARGING = "Charging"
    CHARGING_STATUS_FAULT = "Fault"
    CHARGING_STATUS_UNSPECIFIED = "Unspecified"
    CHARGING_STATUS_SCHEDULED = "Scheduled"
    CHARGING_STATUS_DISCHARGING = "Discharging"
    CHARGING_STATUS_ERROR = "Error"
    CHARGING_STATUS_SMART_CHARGING = "Smart Charging"


@dataclass(frozen=True)
class CarBaseInformation:
    _received_timestamp: datetime


@dataclass(frozen=True)
class CarInformationData(CarBaseInformation):
    vin: str | None
    internal_vehicle_identifier: str | None
    registration_no: str | None
    registration_date: date | None
    factory_complete_date: date | None
    model_name: str | None
    image_url: str | None
    battery: str | None
    torque: str | None
    software_version: str | None
    software_version_timestamp: datetime | None

    @classmethod
    def from_dict(cls, data: GqlDict) -> Self:
        if not isinstance(data, dict):
            raise TypeError

        return cls(
            vin=get_field_name_str("vin", data),
            internal_vehicle_identifier=get_field_name_str(
                "internalVehicleIdentifier", data
            ),
            registration_no=get_field_name_str("registrationNo", data),
            registration_date=get_field_name_date("registrationDate", data),
            factory_complete_date=get_field_name_date("factoryCompleteDate", data),
            model_name=get_field_name_str("content/model/name", data),
            image_url=get_field_name_str("content/images/studio/url", data),
            battery=get_field_name_str("content/specification/battery", data),
            torque=get_field_name_str("content/specification/torque", data),
            software_version=get_field_name_str("software/version", data),
            software_version_timestamp=get_field_name_datetime(
                "software/versionTimestamp", data
            ),
            _received_timestamp=datetime.now(tz=timezone.utc),
        )


@dataclass(frozen=True)
class CarOdometerData(CarBaseInformation):
    average_speed_km_per_hour: int | None
    odometer_meters: int | None
    trip_meter_automatic_km: float | None
    trip_meter_manual_km: float | None
    event_updated_timestamp: datetime | None

    @classmethod
    def from_dict(cls, data: GqlDict) -> Self:
        if not isinstance(data, dict):
            raise TypeError

        return cls(
            average_speed_km_per_hour=get_field_name_int("averageSpeedKmPerHour", data),
            odometer_meters=get_field_name_int("odometerMeters", data),
            trip_meter_automatic_km=get_field_name_float("tripMeterAutomaticKm", data),
            trip_meter_manual_km=get_field_name_float("tripMeterManualKm", data),
            event_updated_timestamp=get_field_name_datetime(
                "eventUpdatedTimestamp/iso", data
            ),
            _received_timestamp=datetime.now(tz=timezone.utc),
        )


@dataclass(frozen=True)
class CarBatteryData(CarBaseInformation):
    average_energy_consumption_kwh_per_100km: float | None
    battery_charge_level_percentage: int | None
    charger_connection_status: ChargingConnectionStatus
    charging_current_amps: int
    charging_power_watts: int
    charging_status: ChargingStatus
    estimated_charging_time_minutes_to_target_distance: int | None
    estimated_charging_time_to_full_minutes: int | None
    estimated_distance_to_empty_km: int | None
    event_updated_timestamp: datetime | None

    @classmethod
    def from_dict(cls, data: GqlDict) -> Self:
        if not isinstance(data, dict):
            raise TypeError

        try:
            charger_connection_status = ChargingConnectionStatus[
                get_field_name_str("chargerConnectionStatus", data)
            ]
        except KeyError:
            charger_connection_status = (
                ChargingConnectionStatus.CHARGER_CONNECTION_STATUS_UNSPECIFIED
            )

        try:
            charging_status = ChargingStatus[get_field_name_str("chargingStatus", data)]
        except KeyError:
            charging_status = ChargingStatus.CHARGING_STATUS_UNSPECIFIED

        return cls(
            average_energy_consumption_kwh_per_100km=get_field_name_float(
                "averageEnergyConsumptionKwhPer100Km", data
            ),
            battery_charge_level_percentage=get_field_name_int(
                "batteryChargeLevelPercentage", data
            ),
            charger_connection_status=charger_connection_status,
            charging_current_amps=get_field_name_int("chargingCurrentAmps", data) or 0,
            charging_power_watts=get_field_name_int("chargingPowerWatts", data) or 0,
            charging_status=charging_status,
            estimated_charging_time_minutes_to_target_distance=get_field_name_int(
                "estimatedChargingTimeMinutesToTargetDistance", data
            ),
            estimated_charging_time_to_full_minutes=get_field_name_int(
                "estimatedChargingTimeToFullMinutes", data
            ),
            estimated_distance_to_empty_km=get_field_name_int(
                "estimatedDistanceToEmptyKm", data
            ),
            event_updated_timestamp=get_field_name_datetime(
                "eventUpdatedTimestamp/iso", data
            ),
            _received_timestamp=datetime.now(tz=timezone.utc),
        )
