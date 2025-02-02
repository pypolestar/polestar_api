"""Support for Polestar sensors."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

import homeassistant.util.dt as dt_util
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    PERCENTAGE,
    EntityCategory,
    UnitOfElectricCurrent,
    UnitOfEnergy,
    UnitOfLength,
    UnitOfPower,
    UnitOfSpeed,
    UnitOfTime,
)

from .entity import (
    PolestarEntity,
    PolestarEntityDataSource,
    PolestarEntityDataSourceException,
    PolestarEntityDescription,
)

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .coordinator import PolestarCoordinator
    from .data import PolestarConfigEntry

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class PolestarSensorDescription(SensorEntityDescription, PolestarEntityDescription):
    """Class to describe an Polestar sensor entity."""


INFORMATION_ENTITY_DESCRIPTIONS: Final[tuple[PolestarSensorDescription, ...]] = (
    PolestarSensorDescription(
        key="internal_vehicle_id",
        icon="mdi:numeric-1-box",
        native_unit_of_measurement=None,
        entity_registry_enabled_default=False,
        data_source=PolestarEntityDataSource.INFORMATION,
        data_attribute="internal_vehicle_identifier",
    ),
    PolestarSensorDescription(
        key="vin",
        icon="mdi:card-account-details",
        native_unit_of_measurement=None,
        data_source=PolestarEntityDataSource.INFORMATION,
        data_attribute="vin",
    ),
    PolestarSensorDescription(
        key="model_name",
        icon="mdi:car-electric",
        native_unit_of_measurement=None,
        data_source=PolestarEntityDataSource.INFORMATION,
        data_attribute="model_name",
    ),
    PolestarSensorDescription(
        key="registration_number",
        icon="mdi:numeric-1-box",
        native_unit_of_measurement=None,
        data_source=PolestarEntityDataSource.INFORMATION,
        data_attribute="registration_no",
    ),
    PolestarSensorDescription(
        key="torque",
        icon="mdi:card-account-details",
        native_unit_of_measurement="Nm",
        data_source=PolestarEntityDataSource.INFORMATION,
        data_attribute="torque_nm",
    ),
    PolestarSensorDescription(
        key="battery_capacity",
        icon="mdi:battery-check",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=0,
        state_class=SensorStateClass.TOTAL,
        device_class=SensorDeviceClass.ENERGY,
        data_source=PolestarEntityDataSource.INFORMATION,
        data_attribute="battery_information",
        data_fn=lambda value: value.capacity if value else None,
    ),
    PolestarSensorDescription(
        key="software_version",
        icon="mdi:information-outline",
        native_unit_of_measurement=None,
        entity_registry_enabled_default=False,
        data_source=PolestarEntityDataSource.INFORMATION,
        data_attribute="software_version",
    ),
    PolestarSensorDescription(
        key="software_version_release",
        icon="mdi:information-outline",
        native_unit_of_measurement=None,
        entity_registry_enabled_default=False,
        data_source=PolestarEntityDataSource.INFORMATION,
        data_attribute="software_version_timestamp",
    ),
)

ODOMETER_ENTITY_DESCRIPTIONS: Final[tuple[PolestarSensorDescription, ...]] = (
    PolestarSensorDescription(
        key="current_odometer",
        icon="mdi:map-marker-distance",
        native_unit_of_measurement=UnitOfLength.METERS,
        suggested_unit_of_measurement=UnitOfLength.KILOMETERS,
        suggested_display_precision=0,
        state_class=SensorStateClass.TOTAL,
        device_class=SensorDeviceClass.DISTANCE,
        data_source=PolestarEntityDataSource.ODOMETER,
        data_attribute="odometer_meters",
    ),
    PolestarSensorDescription(
        key="current_trip_meter_automatic",
        icon="mdi:map-marker-distance",
        native_unit_of_measurement=UnitOfLength.KILOMETERS,
        suggested_display_precision=1,
        state_class=SensorStateClass.TOTAL_INCREASING,
        device_class=SensorDeviceClass.DISTANCE,
        data_source=PolestarEntityDataSource.ODOMETER,
        data_attribute="trip_meter_automatic_km",
    ),
    PolestarSensorDescription(
        key="current_trip_meter_manual",
        icon="mdi:map-marker-distance",
        native_unit_of_measurement=UnitOfLength.KILOMETERS,
        suggested_display_precision=1,
        state_class=SensorStateClass.TOTAL_INCREASING,
        device_class=SensorDeviceClass.DISTANCE,
        data_source=PolestarEntityDataSource.ODOMETER,
        data_attribute="trip_meter_manual_km",
    ),
    PolestarSensorDescription(
        key="average_speed",
        icon="mdi:speedometer",
        native_unit_of_measurement=UnitOfSpeed.KILOMETERS_PER_HOUR,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.SPEED,
        data_source=PolestarEntityDataSource.ODOMETER,
        data_attribute="average_speed_km_per_hour",
    ),
    PolestarSensorDescription(
        key="last_updated_odometer_data",
        icon="mdi:clock",
        native_unit_of_measurement=None,
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        data_source=PolestarEntityDataSource.ODOMETER,
        data_attribute="event_updated_timestamp",
    ),
)

BATTERY_ENTITY_DESCRIPTIONS: Final[tuple[PolestarSensorDescription, ...]] = (
    PolestarSensorDescription(
        key="estimated_range",
        icon="mdi:map-marker-distance",
        native_unit_of_measurement=UnitOfLength.KILOMETERS,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.DISTANCE,
        data_source=PolestarEntityDataSource.BATTERY,
        data_attribute="estimated_distance_to_empty_km",
    ),
    PolestarSensorDescription(
        key="battery_charge_level",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.BATTERY,
        data_source=PolestarEntityDataSource.BATTERY,
        data_attribute="battery_charge_level_percentage",
    ),
    PolestarSensorDescription(
        key="estimated_full_charge_range",
        icon="mdi:map-marker-distance",
        native_unit_of_measurement=UnitOfLength.KILOMETERS,
        suggested_display_precision=0,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.DISTANCE,
        data_source=PolestarEntityDataSource.BATTERY,
        data_attribute="estimated_full_charge_range_km",
    ),
    PolestarSensorDescription(
        key="estimated_charging_time_to_full",
        icon="mdi:battery-clock",
        native_unit_of_measurement=UnitOfTime.MINUTES,
        data_source=PolestarEntityDataSource.BATTERY,
        data_attribute="estimated_charging_time_to_full_minutes",
    ),
    PolestarSensorDescription(
        key="charging_status",
        icon="mdi:ev-station",
        native_unit_of_measurement=None,
        data_source=PolestarEntityDataSource.BATTERY,
        data_attribute="charging_status",
    ),
    PolestarSensorDescription(
        key="charging_power",
        icon="mdi:lightning-bolt",
        native_unit_of_measurement=UnitOfPower.WATT,
        suggested_display_precision=0,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.POWER,
        data_source=PolestarEntityDataSource.BATTERY,
        data_attribute="charging_power_watts",
    ),
    PolestarSensorDescription(
        key="charging_current",
        icon="mdi:current-ac",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        suggested_display_precision=0,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.CURRENT,
        data_source=PolestarEntityDataSource.BATTERY,
        data_attribute="charging_current_amps",
    ),
    PolestarSensorDescription(
        key="charger_connection_status",
        icon="mdi:connection",
        native_unit_of_measurement=None,
        device_class=None,
        data_source=PolestarEntityDataSource.BATTERY,
        data_attribute="charger_connection_status",
    ),
    PolestarSensorDescription(
        key="average_energy_consumption",
        icon="mdi:battery-clock",
        native_unit_of_measurement="kWh/100km",
        suggested_display_precision=1,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=None,
        data_source=PolestarEntityDataSource.BATTERY,
        data_attribute="average_energy_consumption_kwh_per_100km",
    ),
    PolestarSensorDescription(
        key="estimated_charging_time_to_target_distance",
        icon="mdi:battery-clock",
        native_unit_of_measurement=UnitOfTime.MINUTES,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=None,
        data_source=PolestarEntityDataSource.BATTERY,
        data_attribute="estimated_charging_time_minutes_to_target_distance",
    ),
    PolestarSensorDescription(
        key="estimated_fully_charged_time",
        icon="mdi:battery-clock",
        native_unit_of_measurement=None,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.DURATION,
        data_source=PolestarEntityDataSource.BATTERY,
        data_attribute="estimated_fully_charged",
        data_fn=lambda value: dt_util.as_local(value).strftime("%Y-%m-%d %H:%M:%S"),
    ),
    PolestarSensorDescription(
        key="last_updated_battery_data",
        icon="mdi:clock",
        native_unit_of_measurement=None,
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        data_source=PolestarEntityDataSource.BATTERY,
        data_attribute="event_updated_timestamp",
    ),
)

HEALTH_ENTITY_DESCRIPTIONS: Final[tuple[PolestarSensorDescription, ...]] = (
    PolestarSensorDescription(
        key="days_to_service",
        icon="mdi:calendar",
        native_unit_of_measurement=UnitOfTime.DAYS,
        suggested_display_precision=0,
        data_source=PolestarEntityDataSource.HEALTH,
        data_attribute="days_to_service",
    ),
    PolestarSensorDescription(
        key="distance_to_service",
        icon="mdi:map-marker-distance",
        native_unit_of_measurement=UnitOfLength.KILOMETERS,
        suggested_display_precision=0,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.DISTANCE,
        data_source=PolestarEntityDataSource.HEALTH,
        data_attribute="distance_to_service_km",
    ),
    PolestarSensorDescription(
        key="brake_fluid_level_warning",
        icon="mdi:alert",
        native_unit_of_measurement=None,
        data_source=PolestarEntityDataSource.HEALTH,
        data_attribute="brake_fluid_level_warning",
    ),
    PolestarSensorDescription(
        key="engine_coolant_level_warning",
        icon="mdi:alert",
        native_unit_of_measurement=None,
        data_source=PolestarEntityDataSource.HEALTH,
        data_attribute="engine_coolant_level_warning",
    ),
    PolestarSensorDescription(
        key="oil_level_warning",
        icon="mdi:alert",
        native_unit_of_measurement=None,
        data_source=PolestarEntityDataSource.HEALTH,
        data_attribute="oil_level_warning",
    ),
    PolestarSensorDescription(
        key="service_warning",
        icon="mdi:alert",
        native_unit_of_measurement=None,
        data_source=PolestarEntityDataSource.HEALTH,
        data_attribute="service_warning",
    ),
    PolestarSensorDescription(
        key="last_updated_health_data",
        icon="mdi:clock",
        native_unit_of_measurement=None,
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        data_source=PolestarEntityDataSource.HEALTH,
        data_attribute="event_updated_timestamp",
    ),
)

API_ENTITY_DESCRIPTIONS: Final[tuple[PolestarSensorDescription, ...]] = (
    PolestarSensorDescription(
        key="api_status_code_data",
        icon="mdi:heart",
        native_unit_of_measurement=None,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    PolestarSensorDescription(
        key="api_status_code_auth",
        icon="mdi:heart",
        native_unit_of_measurement=None,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    PolestarSensorDescription(
        key="api_token_expires_at",
        icon="mdi:clock-time-eight",
        native_unit_of_measurement=None,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
)

ENTITY_DESCRIPTIONS: Final[tuple[PolestarSensorDescription, ...]] = (
    *INFORMATION_ENTITY_DESCRIPTIONS,
    *ODOMETER_ENTITY_DESCRIPTIONS,
    *BATTERY_ENTITY_DESCRIPTIONS,
    *HEALTH_ENTITY_DESCRIPTIONS,
    *API_ENTITY_DESCRIPTIONS,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PolestarConfigEntry,
    async_add_entities: AddEntitiesCallback,
):
    """Set up using config_entry."""
    async_add_entities(
        [
            PolestarSensor(coordinator, entity_description)
            for coordinator in entry.runtime_data.coordinators
            for entity_description in ENTITY_DESCRIPTIONS
        ]
    )


class PolestarSensor(PolestarEntity, SensorEntity):
    """Representation of a Polestar Sensor."""

    entity_description: PolestarSensorDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: PolestarCoordinator,
        entity_description: PolestarSensorDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entity_description)

        match self.entity_description.key:
            case "vin":
                self._attr_extra_state_attributes = {
                    "factory_complete_date": getattr(
                        self.coordinator.car_information_data,
                        "factory_complete_date",
                        None,
                    )
                }
            case "registration_number":
                self._attr_extra_state_attributes = {
                    "registration_date": getattr(
                        self.coordinator.car_information_data,
                        "registration_date",
                        None,
                    )
                }

    @property
    def native_value(self) -> str | None:
        """Return the native value of the sensor."""
        try:
            if value := self.get_native_value():
                return value
        except PolestarEntityDataSourceException:
            _LOGGER.debug("Fallback to data dict %s", self.entity_description.key)
            return self.coordinator.data.get(self.entity_description.key)
