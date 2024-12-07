"""Support for Polestar sensors."""

import logging
from contextlib import suppress
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Final

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
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType
from homeassistant.util.unit_conversion import (
    DistanceConverter,
    EnergyConverter,
    SpeedConverter,
)

from .const import DOMAIN as POLESTAR_API_DOMAIN
from .data import PolestarConfigEntry
from .entity import PolestarEntity
from .polestar import PolestarCar

_LOGGER = logging.getLogger(__name__)
SCAN_INTERVAL = timedelta(seconds=60)


@dataclass
class PolestarSensorDescriptionMixin:
    """Define an entity description mixin for sensor entities."""

    round_digits: int | None
    max_value: int | None


@dataclass
class PolestarSensorDescription(
    SensorEntityDescription, PolestarSensorDescriptionMixin
):
    """Class to describe an Polestar sensor entity."""


API_STATUS_DICT = {
    200: "OK",
    303: "OK",
    401: "Unauthorized",
    404: "API Down",
    500: "Internal Server Error",
}


POLESTAR_SENSOR_TYPES: Final[tuple[PolestarSensorDescription, ...]] = (
    PolestarSensorDescription(
        key="estimate_range",
        name="Range",
        icon="mdi:map-marker-distance",
        native_unit_of_measurement=UnitOfLength.KILOMETERS,
        round_digits=2,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.DISTANCE,
        max_value=660,
    ),
    PolestarSensorDescription(
        key="current_odometer",
        name="Odometer",
        icon="mdi:map-marker-distance",
        native_unit_of_measurement=UnitOfLength.METERS,
        suggested_unit_of_measurement=UnitOfLength.KILOMETERS,
        suggested_display_precision=0,
        round_digits=2,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.DISTANCE,
        max_value=1000000000,
    ),
    PolestarSensorDescription(
        key="average_speed",
        name="Average Speed",
        icon="mdi:speedometer",
        native_unit_of_measurement=UnitOfSpeed.KILOMETERS_PER_HOUR,
        round_digits=None,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.SPEED,
        max_value=150,
    ),
    PolestarSensorDescription(
        key="current_trip_meter_automatic",
        name="Trip Meter Automatic",
        icon="mdi:map-marker-distance",
        native_unit_of_measurement=UnitOfLength.KILOMETERS,
        suggested_display_precision=1,
        round_digits=2,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.DISTANCE,
        max_value=100000,
    ),
    PolestarSensorDescription(
        key="current_trip_meter_manual",
        name="Trip Meter Manual",
        icon="mdi:map-marker-distance",
        native_unit_of_measurement=UnitOfLength.KILOMETERS,
        suggested_display_precision=1,
        round_digits=2,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.DISTANCE,
        max_value=100000,
    ),
    PolestarSensorDescription(
        key="battery_charge_level",
        name="Battery Level",
        native_unit_of_measurement=PERCENTAGE,
        round_digits=0,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.BATTERY,
        max_value=100,
    ),
    PolestarSensorDescription(
        key="estimated_charging_time_to_full",
        name="Charging Time",
        icon="mdi:battery-clock",
        native_unit_of_measurement=UnitOfTime.MINUTES,
        round_digits=None,
        max_value=None,
    ),
    PolestarSensorDescription(
        key="charging_status",
        name="Charging Status",
        icon="mdi:ev-station",
        native_unit_of_measurement=None,
        round_digits=None,
        max_value=None,
    ),
    PolestarSensorDescription(
        key="charging_power",
        name="Charging Power",
        icon="mdi:lightning-bolt",
        native_unit_of_measurement=UnitOfPower.WATT,
        suggested_display_precision=0,
        round_digits=None,
        max_value=None,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.POWER,
    ),
    PolestarSensorDescription(
        key="charging_current",
        name="Charging Current",
        icon="mdi:current-ac",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        suggested_display_precision=0,
        round_digits=None,
        max_value=None,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.CURRENT,
    ),
    PolestarSensorDescription(
        key="charger_connection_status",
        name="Charging Connection Status",
        icon="mdi:connection",
        native_unit_of_measurement=None,
        round_digits=None,
        max_value=None,
        device_class=None,
    ),
    PolestarSensorDescription(
        key="average_energy_consumption_kwh_per_100",
        name="Avg. Energy Consumption",
        icon="mdi:battery-clock",
        native_unit_of_measurement="kWh/100km",
        suggested_display_precision=1,
        round_digits=None,
        max_value=None,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=None,
    ),
    PolestarSensorDescription(
        key="estimated_charging_time_minutes_to_target_distance",
        name="Estimated Charging Time To Target Distance",
        icon="mdi:battery-clock",
        native_unit_of_measurement=UnitOfTime.MINUTES,
        round_digits=None,
        max_value=None,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=None,
    ),
    PolestarSensorDescription(
        key="vin",
        name="VIN",
        icon="mdi:card-account-details",
        native_unit_of_measurement=None,
        round_digits=None,
        max_value=None,
    ),
    PolestarSensorDescription(
        key="software_version",
        name="Software Version",
        icon="mdi:information-outline",
        native_unit_of_measurement=None,
        round_digits=None,
        max_value=None,
    ),
    PolestarSensorDescription(
        key="software_version_release",
        name="Software Released",
        icon="mdi:information-outline",
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.TIMESTAMP,
        native_unit_of_measurement=None,
        round_digits=None,
        max_value=None,
    ),
    PolestarSensorDescription(
        key="registration_number",
        name="Registration Number",
        icon="mdi:numeric-1-box",
        native_unit_of_measurement=None,
        round_digits=None,
        max_value=None,
    ),
    PolestarSensorDescription(
        key="internal_vehicle_id",
        name="Internal Vehicle ID",
        icon="mdi:numeric-1-box",
        native_unit_of_measurement=None,
        round_digits=None,
        max_value=None,
        entity_registry_enabled_default=False,
    ),
    PolestarSensorDescription(
        key="estimated_fully_charged_time",
        name="Time Full Charged",
        icon="mdi:battery-clock",
        native_unit_of_measurement=None,
        round_digits=None,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.DURATION,
        max_value=None,
    ),
    PolestarSensorDescription(
        key="model_name",
        name="Model Name",
        icon="mdi:car-electric",
        native_unit_of_measurement=None,
        round_digits=None,
        max_value=None,
    ),
    PolestarSensorDescription(
        key="last_updated_odometer_data",
        name="Last Updated Odometer Data",
        icon="mdi:clock",
        native_unit_of_measurement=None,
        round_digits=None,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        max_value=None,
    ),
    PolestarSensorDescription(
        key="last_updated_battery_data",
        name="Last Updated Battery Data",
        icon="mdi:clock",
        native_unit_of_measurement=None,
        round_digits=None,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        max_value=None,
    ),
    PolestarSensorDescription(
        key="estimate_full_charge_range",
        name="Calc. Full Charge Range",
        icon="mdi:map-marker-distance",
        native_unit_of_measurement=UnitOfLength.KILOMETERS,
        suggested_display_precision=0,
        round_digits=None,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.DISTANCE,
        max_value=660,  # WLTP range max 655
    ),
    PolestarSensorDescription(
        key="api_status_code_data",
        name="API Status Code (Data)",
        icon="mdi:heart",
        native_unit_of_measurement=None,
        round_digits=None,
        max_value=None,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    PolestarSensorDescription(
        key="api_status_code_auth",
        name="API Status Code (Auth)",
        icon="mdi:heart",
        native_unit_of_measurement=None,
        round_digits=None,
        max_value=None,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    PolestarSensorDescription(
        key="api_token_expires_at",
        name="Auth Token Expired At",
        icon="mdi:clock-time-eight",
        native_unit_of_measurement=None,
        round_digits=None,
        max_value=None,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    PolestarSensorDescription(
        key="torque",
        name="Torque",
        icon="mdi:card-account-details",
        native_unit_of_measurement="Nm",
        round_digits=None,
        max_value=None,
    ),
    PolestarSensorDescription(
        key="battery_capacity",
        name="Battery Capacity",
        icon="mdi:battery-check",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=0,
        round_digits=None,
        max_value=None,
        state_class=SensorStateClass.TOTAL,
        device_class=SensorDeviceClass.ENERGY,
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
            PolestarSensor(car, entity_description)
            for entity_description in POLESTAR_SENSOR_TYPES
            for car in entry.runtime_data.cars
        ]
    )


class PolestarSensor(PolestarEntity, SensorEntity):
    """Representation of a Polestar Sensor."""

    entity_description: PolestarSensorDescription
    _attr_has_entity_name = True

    def __init__(
        self, car: PolestarCar, entity_description: PolestarSensorDescription
    ) -> None:
        """Initialize the sensor."""
        super().__init__(car)
        self.car = car
        self.entity_description = entity_description
        self.entity_id = f"{POLESTAR_API_DOMAIN}.'polestar_'.{car.get_short_id()}_{entity_description.key}"
        # self._attr_name = f"{description.name}"
        self._attr_unique_id = (
            f"polestar_{car.get_unique_id()}_{entity_description.key}"
        )
        self._attr_translation_key = f"polestar_{entity_description.key}"
        self._attr_native_unit_of_measurement = (
            entity_description.native_unit_of_measurement
        )
        self._sensor_data = None
        self._attr_unit_of_measurement = entity_description.native_unit_of_measurement
        self._attr_native_value = self.car.data.get(self.entity_description.key)
        self._attr_extra_state_attributes = {}

        if entity_description.round_digits is not None:
            self.attr_suggested_display_precision = entity_description.round_digits

        if entity_description.state_class is not None:
            self._attr_state_class = entity_description.state_class
        if entity_description.device_class is not None:
            self._attr_device_class = entity_description.device_class
        if self.car is not None and self.car.polestar_api.latest_call_code == 200:
            self._async_update_attrs()

    @callback
    def _async_update_attrs(self) -> None:
        """Update the state and attributes."""
        self._attr_native_value = self._sensor_data = self.car.data.get(
            self.entity_description.key
        )

    @property
    def icon(self) -> str | None:
        """Return the icon of the sensor."""
        return self.entity_description.icon

    @property
    def state(self) -> StateType:
        """Return the state of the sensor."""
        if self._attr_native_value is None and self.entity_description.key in (
            "estimated_charging_time_minutes_to_target_distance"
        ):
            # self.entity_description.native_unit_of_measurement = None
            self._attr_native_unit_of_measurement = None
            return "Not Supported Yet"

        if self.entity_description.key == "vin":
            self._attr_extra_state_attributes = {
                "factory_complete_date": self.car.data.get("factory_complete_date")
            }

        if self.entity_description.key == "registration_number":
            self._attr_extra_state_attributes = {
                "registration_date": self.car.data.get("registration_date")
            }

        if self._attr_native_value != 0 and self._attr_native_value in (None, False):
            return None

        # if GUI changed the unit, we need to convert the value
        if self._sensor_data:  # noqa
            if self._sensor_option_unit_of_measurement is not None:
                if self._sensor_option_unit_of_measurement in (
                    UnitOfLength.MILES,
                    UnitOfLength.KILOMETERS,
                    UnitOfLength.METERS,
                    UnitOfLength.CENTIMETERS,
                    UnitOfLength.MILLIMETERS,
                    UnitOfLength.INCHES,
                    UnitOfLength.FEET,
                    UnitOfLength.YARDS,
                ):
                    self._attr_native_value = DistanceConverter.convert(
                        self._sensor_data,
                        self.entity_description.native_unit_of_measurement,
                        self._sensor_option_unit_of_measurement,
                    )
                    self._attr_native_unit_of_measurement = (
                        self._sensor_option_unit_of_measurement
                    )
                elif self._sensor_option_unit_of_measurement in (
                    UnitOfSpeed.MILES_PER_HOUR,
                    UnitOfSpeed.KILOMETERS_PER_HOUR,
                    UnitOfSpeed.METERS_PER_SECOND,
                    UnitOfSpeed.KNOTS,
                ):
                    self._attr_native_value = SpeedConverter.convert(
                        self._sensor_data,
                        self.entity_description.native_unit_of_measurement,
                        self._sensor_option_unit_of_measurement,
                    )
                    self._attr_native_unit_of_measurement = (
                        self._sensor_option_unit_of_measurement
                    )
                elif self._sensor_option_unit_of_measurement in (
                    UnitOfEnergy.WATT_HOUR,
                    UnitOfEnergy.KILO_WATT_HOUR,
                    UnitOfEnergy.MEGA_WATT_HOUR,
                    UnitOfEnergy.GIGA_JOULE,
                    UnitOfEnergy.MEGA_JOULE,
                ):
                    self._attr_native_value = EnergyConverter.convert(
                        float(self._sensor_data),
                        self.entity_description.native_unit_of_measurement,
                        self._sensor_option_unit_of_measurement,
                    )
                    self._attr_native_unit_of_measurement = (
                        self._sensor_option_unit_of_measurement
                    )

        if self.entity_description.key in (
            "estimate_range",
            "estimate_full_charge_range",
        ):
            if self._sensor_option_unit_of_measurement == UnitOfLength.MILES:
                self.entity_description.max_value = 410
            elif self._sensor_option_unit_of_measurement == UnitOfLength.KILOMETERS:
                self.entity_description.max_value = 660
            elif self._sensor_option_unit_of_measurement == UnitOfLength.METERS:
                self.entity_description.max_value = 660000

        # prevent exponentianal value, we only give state value that is lower than the max value
        if self.entity_description.max_value is not None:
            if isinstance(self._sensor_data, str):
                self._attr_native_value = int(self._sensor_data)
            if self._attr_native_value > self.entity_description.max_value:
                _LOGGER.warning(
                    "%s: Value %s is higher than max value %s",
                    self.entity_description.key,
                    self._attr_native_value,
                    self.entity_description.max_value,
                )
                return None

        # only round value if native value is not None
        if self._attr_native_value:  # noqa
            # round the value
            if self.entity_description.round_digits is not None:  # noqa
                # if the value is integer, remove the decimal
                if self.entity_description.round_digits == 0 and isinstance(
                    self._attr_native_value, int
                ):
                    self._attr_native_value = int(self._attr_native_value)
                    with suppress(ValueError):
                        self._attr_native_value = round(
                            float(self._attr_native_value),
                            self.entity_description.round_digits,
                        )

        return self._attr_native_value

    @property
    def unit_of_measurement(self) -> str:
        """Return the unit of measurement."""
        return self.native_unit_of_measurement

    async def async_update(self) -> None:
        """Get the latest data and updates the states."""
        try:
            await self.car.async_update()
            value = self.car.data.get(self.entity_description.key)
            if value is not None:
                self._attr_native_value = value
                self._sensor_data = value

        except Exception as exc:
            _LOGGER.warning(
                "Failed to update sensor async update: %s", exc, exc_info=exc
            )
            self.car.polestar_api.next_update = datetime.now() + timedelta(seconds=60)
