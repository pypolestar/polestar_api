"""Support for Polestar sensors."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Final

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

from .entity import PolestarEntity

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .coordinator import PolestarCoordinator
    from .data import PolestarConfigEntry

_LOGGER = logging.getLogger(__name__)


class PolestarSensorDescription(SensorEntityDescription):
    """Class to describe an Polestar sensor entity."""


ENTITY_DESCRIPTIONS: Final[tuple[PolestarSensorDescription, ...]] = (
    PolestarSensorDescription(
        key="estimated_range",
        icon="mdi:map-marker-distance",
        native_unit_of_measurement=UnitOfLength.KILOMETERS,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.DISTANCE,
    ),
    PolestarSensorDescription(
        key="current_odometer",
        icon="mdi:map-marker-distance",
        native_unit_of_measurement=UnitOfLength.METERS,
        suggested_unit_of_measurement=UnitOfLength.KILOMETERS,
        suggested_display_precision=0,
        state_class=SensorStateClass.TOTAL,
        device_class=SensorDeviceClass.DISTANCE,
    ),
    PolestarSensorDescription(
        key="average_speed",
        icon="mdi:speedometer",
        native_unit_of_measurement=UnitOfSpeed.KILOMETERS_PER_HOUR,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.SPEED,
    ),
    PolestarSensorDescription(
        key="current_trip_meter_automatic",
        icon="mdi:map-marker-distance",
        native_unit_of_measurement=UnitOfLength.KILOMETERS,
        suggested_display_precision=1,
        state_class=SensorStateClass.TOTAL_INCREASING,
        device_class=SensorDeviceClass.DISTANCE,
    ),
    PolestarSensorDescription(
        key="current_trip_meter_manual",
        icon="mdi:map-marker-distance",
        native_unit_of_measurement=UnitOfLength.KILOMETERS,
        suggested_display_precision=1,
        state_class=SensorStateClass.TOTAL_INCREASING,
        device_class=SensorDeviceClass.DISTANCE,
    ),
    PolestarSensorDescription(
        key="battery_charge_level",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.BATTERY,
    ),
    PolestarSensorDescription(
        key="estimated_charging_time_to_full",
        icon="mdi:battery-clock",
        native_unit_of_measurement=UnitOfTime.MINUTES,
    ),
    PolestarSensorDescription(
        key="charging_status",
        icon="mdi:ev-station",
        native_unit_of_measurement=None,
    ),
    PolestarSensorDescription(
        key="charging_power",
        icon="mdi:lightning-bolt",
        native_unit_of_measurement=UnitOfPower.WATT,
        suggested_display_precision=0,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.POWER,
    ),
    PolestarSensorDescription(
        key="charging_current",
        icon="mdi:current-ac",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        suggested_display_precision=0,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.CURRENT,
    ),
    PolestarSensorDescription(
        key="charger_connection_status",
        icon="mdi:connection",
        native_unit_of_measurement=None,
        device_class=None,
    ),
    PolestarSensorDescription(
        key="average_energy_consumption",
        icon="mdi:battery-clock",
        native_unit_of_measurement="kWh/100km",
        suggested_display_precision=1,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=None,
    ),
    PolestarSensorDescription(
        key="estimated_charging_time_to_target_distance",
        icon="mdi:battery-clock",
        native_unit_of_measurement=UnitOfTime.MINUTES,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=None,
    ),
    PolestarSensorDescription(
        key="vin",
        icon="mdi:card-account-details",
        native_unit_of_measurement=None,
    ),
    PolestarSensorDescription(
        key="software_version",
        icon="mdi:information-outline",
        native_unit_of_measurement=None,
        entity_registry_enabled_default=False,
    ),
    PolestarSensorDescription(
        key="software_version_release",
        icon="mdi:information-outline",
        native_unit_of_measurement=None,
        entity_registry_enabled_default=False,
    ),
    PolestarSensorDescription(
        key="registration_number",
        icon="mdi:numeric-1-box",
        native_unit_of_measurement=None,
    ),
    PolestarSensorDescription(
        key="internal_vehicle_id",
        icon="mdi:numeric-1-box",
        native_unit_of_measurement=None,
        entity_registry_enabled_default=False,
    ),
    PolestarSensorDescription(
        key="estimated_fully_charged_time",
        icon="mdi:battery-clock",
        native_unit_of_measurement=None,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.DURATION,
    ),
    PolestarSensorDescription(
        key="model_name",
        icon="mdi:car-electric",
        native_unit_of_measurement=None,
    ),
    PolestarSensorDescription(
        key="last_updated_odometer_data",
        icon="mdi:clock",
        native_unit_of_measurement=None,
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    PolestarSensorDescription(
        key="last_updated_battery_data",
        icon="mdi:clock",
        native_unit_of_measurement=None,
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    PolestarSensorDescription(
        key="last_updated_health_data",
        icon="mdi:clock",
        native_unit_of_measurement=None,
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    PolestarSensorDescription(
        key="estimated_full_charge_range",
        icon="mdi:map-marker-distance",
        native_unit_of_measurement=UnitOfLength.KILOMETERS,
        suggested_display_precision=0,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.DISTANCE,
    ),
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
    PolestarSensorDescription(
        key="torque",
        icon="mdi:card-account-details",
        native_unit_of_measurement="Nm",
    ),
    PolestarSensorDescription(
        key="battery_capacity",
        icon="mdi:battery-check",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=0,
        state_class=SensorStateClass.TOTAL,
        device_class=SensorDeviceClass.ENERGY,
    ),
    PolestarSensorDescription(
        key="days_to_service",
        icon="mdi:calendar",
        native_unit_of_measurement=UnitOfTime.DAYS,
        suggested_display_precision=0,
    ),
    PolestarSensorDescription(
        key="distance_to_service",
        icon="mdi:map-marker-distance",
        native_unit_of_measurement=UnitOfLength.KILOMETERS,
        suggested_display_precision=0,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.DISTANCE,
    ),
    PolestarSensorDescription(
        key="brake_fluid_level_warning",
        icon="mdi:alert",
        native_unit_of_measurement=None,
    ),
    PolestarSensorDescription(
        key="engine_coolant_level_warning",
        icon="mdi:alert",
        native_unit_of_measurement=None,
    ),
    PolestarSensorDescription(
        key="oil_level_warning",
        icon="mdi:alert",
        native_unit_of_measurement=None,
    ),
    PolestarSensorDescription(
        key="service_warning",
        icon="mdi:alert",
        native_unit_of_measurement=None,
    ),
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
                    "factory_complete_date": self.coordinator.data.get(
                        "factory_complete_date"
                    )
                }
            case "registration_number":
                self._attr_extra_state_attributes = {
                    "registration_date": self.coordinator.data.get("registration_date")
                }

    @property
    def native_value(self) -> str | None:
        """Return the native value of the sensor."""
        return self.coordinator.data.get(self.entity_description.key)
