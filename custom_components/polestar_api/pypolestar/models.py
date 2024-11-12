from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum
from typing import Self

from .utils import get_field_name_date, get_field_name_datetime, get_field_name_str


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
class CarInformation:
    vin: str
    internal_vehicle_identifier: str
    registration_no: str | None
    registration_date: date | None
    factory_complete_date: date | None
    image_url: str | None
    battery: str | None
    torque: str | None
    software_version: str | None

    @classmethod
    def from_dict(cls, data) -> Self:
        return cls(
            vin=data["vin"],
            internal_vehicle_identifier=data["internalVehicleIdentifier"],
            registration_no=data.get("registrationNo"),
            registration_date=get_field_name_date("registrationDate", data),
            factory_complete_date=get_field_name_date("factoryCompleteDate", data),
            image_url=get_field_name_str("content/images/studio/url", data),
            battery=get_field_name_str("content/specification/battery", data),
            torque=get_field_name_str("content/specification/torque", data),
            software_version=get_field_name_str("software/version", data),
        )


@dataclass(frozen=True)
class CarOdometerData:
    average_speed_km_per_hour: float | None
    odometer_meters: int | None
    trip_meter_automatic_km: int | None
    trip_meter_manual_km: int | None
    event_update_timestamp: datetime | None

    @classmethod
    def from_dict(cls, data) -> Self:
        return cls(
            average_speed_km_per_hour=int(data["averageSpeedKmPerHour"]),
            odometer_meters=int(data["odometerMeters"]),
            trip_meter_automatic_km=int(data["tripMeterAutomaticKm"]),
            trip_meter_manual_km=int(data["tripMeterManualKm"]),
            event_update_timestamp=get_field_name_datetime(
                "eventUpdatedTimestamp/iso", data
            ),
        )


@dataclass(frozen=True)
class CarBatteryData:
    average_energy_consumption_kwh_per_100km: float
    battery_charge_level_percentage: int
    charger_connection_status: ChargingConnectionStatus
    charging_current_amps: int | None
    charging_power_watts: int | None
    charging_status: ChargingStatus
    estimated_charging_time_minutes_to_target_distance: int
    estimated_charging_time_to_full_minutes: int
    estimated_distance_to_empty_km: int
    event_update_timestamp: datetime | None

    @classmethod
    def from_dict(cls, data) -> Self:
        return cls(
            average_energy_consumption_kwh_per_100km=data[
                "averageEnergyConsumptionKwhPer100Km"
            ],
            battery_charge_level_percentage=data["batteryChargeLevelPercentage"],
            charger_connection_status=ChargingConnectionStatus[
                data["chargerConnectionStatus"]
            ],
            charging_current_amps=data.get("chargingCurrentAmps"),
            charging_power_watts=data.get("chargingPowerWatts"),
            charging_status=ChargingStatus[data["chargingStatus"]],
            estimated_charging_time_minutes_to_target_distance=data[
                "estimatedChargingTimeMinutesToTargetDistance"
            ],
            estimated_charging_time_to_full_minutes=data[
                "estimatedChargingTimeToFullMinutes"
            ],
            estimated_distance_to_empty_km=data["estimatedDistanceToEmptyKm"],
            event_update_timestamp=get_field_name_datetime(
                "eventUpdatedTimestamp/iso", data
            ),
        )
