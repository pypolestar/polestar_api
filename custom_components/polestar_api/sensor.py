import logging

from datetime import datetime, timedelta
from typing import Final
from dataclasses import dataclass
from .entity import PolestarEntity
from homeassistant.helpers.typing import StateType
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.components.sensor import (
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
    SensorDeviceClass

)
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers import entity_platform
from . import DOMAIN as POLESTAR_API_DOMAIN
from .polestar import Polestar
from homeassistant.const import (
    PERCENTAGE,
)


_LOGGER = logging.getLogger(__name__)
SCAN_INTERVAL = timedelta(seconds=15)


@dataclass
class PolestarSensorDescriptionMixin:
    """Define an entity description mixin for sensor entities."""

    query: str
    field_name: str
    round_digits: int | None
    unit: str | None
    max_value: int | None
    dict_data: dict | None


@dataclass
class PolestarSensorDescription(
    SensorEntityDescription,  PolestarSensorDescriptionMixin
):
    """Class to describe an Polestar sensor entity."""


CHARGING_CONNECTION_STATUS_DICT = {
    "CHARGER_CONNECTION_STATUS_CONNECTED": "Connected",
    "CHARGER_CONNECTION_STATUS_DISCONNECTED": "Disconnected",
}

CHARGING_STATUS_DICT = {
    "CHARGING_STATUS_DONE": "Done",
    "CHARGING_STATUS_IDLE": "Idle",
    "CHARGING_STATUS_CHARGING": "Charging",
    "CHARGING_STATUS_FAULT": "Fault",
    "CHARGING_STATUS_UNSPECIFIED": "Unspecified",
    "CHARGING_STATUS_SCHEDULED": "Scheduled",

}

API_STATUS_DICT = {
    200: "OK",
    303: "OK",
    401: "Unauthorized",
    404: "API Down",
    500: "Internal Server Error",
}


POLESTAR_SENSOR_TYPES: Final[tuple[PolestarSensorDescription, ...]] = (
    PolestarSensorDescription(
        key="estimate_distance_to_empty_miles",
        name="Distance miles Remaining",
        icon="mdi:map-marker-distance",
        query="getBatteryData",
        field_name="estimatedDistanceToEmptyMiles",
        unit='miles',
        round_digits=None,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.DISTANCE,
        max_value=None,
        dict_data=None
    ),
    PolestarSensorDescription(
        key="estimate_distance_to_empty_km",
        name="Distance km Remaining",
        icon="mdi:map-marker-distance",
        query="getBatteryData",
        field_name="estimatedDistanceToEmptyKm",
        unit='km',
        round_digits=None,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.DISTANCE,
        max_value=None,
        dict_data=None
    ),
    PolestarSensorDescription(
        key="current_odometer_meters",
        name="Odometer Meter",
        icon="mdi:map-marker-distance",
        query="getOdometerData",
        field_name="odometerMeters",
        unit='km',
        round_digits=None,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.DISTANCE,
        max_value=None,
        dict_data=None
    ),
    PolestarSensorDescription(
        key="average_speed_km_per_hour",
        name="Avg Speed Per Hour",
        icon="mdi:map-marker-distance",
        query="getOdometerData",
        field_name="averageSpeedKmPerHour",
        unit='km',
        round_digits=None,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.DISTANCE,
        max_value=None,
        dict_data=None
    ),
    PolestarSensorDescription(
        key="current_trip_meter_automatic",
        name="Trip Meter Automatic",
        icon="mdi:map-marker-distance",
        query="getOdometerData",
        field_name="tripMeterAutomaticKm",
        unit='km',
        round_digits=None,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.DISTANCE,
        max_value=None,
        dict_data=None
    ),
    PolestarSensorDescription(
        key="current_trip_meter_manual",
        name="Trip Meter Manual",
        icon="mdi:map-marker-distance",
        query="getOdometerData",
        field_name="tripMeterManualKm",
        unit='km',
        round_digits=None,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.DISTANCE,
        max_value=None,
        dict_data=None
    ),
    PolestarSensorDescription(
        key="battery_charge_level",
        name="Battery level",
        query="getBatteryData",
        field_name="batteryChargeLevelPercentage",
        unit=PERCENTAGE,
        round_digits=0,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.BATTERY,
        max_value=None,
        dict_data=None
    ),
    PolestarSensorDescription(
        key="estimated_charging_time_to_full_minutes",
        name="Charging time",
        icon="mdi:battery-clock",
        query="getBatteryData",
        field_name="estimatedChargingTimeToFullMinutes",
        unit='Minutes',
        round_digits=None,
        max_value=None,
        dict_data=None
    ),
    PolestarSensorDescription(
        key="charging_status",
        name="Charging status",
        icon="mdi:battery-clock",
        query="getBatteryData",
        field_name="chargingStatus",
        unit=None,
        round_digits=None,
        max_value=None,
        dict_data=CHARGING_STATUS_DICT
    ),
    PolestarSensorDescription(
        key="charging_power_watts",
        name="Charging Power",
        icon="mdi:lightning-bolt",
        query="getBatteryData",
        field_name="chargingPowerWatts",
        unit='W',
        round_digits=None,
        max_value=None,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.POWER,
        dict_data=None
    ),
    PolestarSensorDescription(
        key="charging_current_amps",
        name="Charging Current",
        icon="mdi:current-ac",
        query="getBatteryData",
        field_name="chargingCurrentAmps",
        unit='A',
        round_digits=None,
        max_value=None,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.POWER,
        dict_data=None
    ),
    PolestarSensorDescription(
        key="charger_connection_status",
        name="Charging Connection Status",
        icon="mdi:battery-clock",
        query="getBatteryData",
        field_name="chargerConnectionStatus",
        unit=None,
        round_digits=None,
        max_value=None,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.POWER,
        dict_data=CHARGING_CONNECTION_STATUS_DICT
    ),
    PolestarSensorDescription(
        key="average_energy_consumption_kwh_per_100_km",
        name="Avg. energy consumption",
        icon="mdi:battery-clock",
        query="getBatteryData",
        field_name="averageEnergyConsumptionKwhPer100Km",
        unit='Kwh/100km',
        round_digits=None,
        max_value=None,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.POWER,
        dict_data=None
    ),
    PolestarSensorDescription(
        key="estimated_charging_time_minutes_to_target_distance",
        name="Estimated charging time to target distance",
        icon="mdi:battery-clock",
        query="getBatteryData",
        field_name="estimatedChargingTimeMinutesToTargetDistance",
        unit=PERCENTAGE,
        round_digits=None,
        max_value=None,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.POWER,
        dict_data=None
    ),
    PolestarSensorDescription(
        key="vin",
        name="VIN",
        icon="mdi:card-account-details",
        query="getConsumerCarsV2",
        field_name="vin",
        unit=None,
        round_digits=None,
        max_value=None,
        dict_data=None
    ),
    PolestarSensorDescription(
        key="registration_number",
        name="Registration number",
        icon="mdi:numeric-1-box",
        query="getConsumerCarsV2",
        field_name="registrationNo",
        unit=None,
        round_digits=None,
        max_value=None,
        dict_data=None
    ),
    PolestarSensorDescription(
        key="estimated_fully_charged_time",
        name="Time Full charged",
        icon="mdi:battery-clock",
        query="getBatteryData",
        field_name="estimatedChargingTimeToFullMinutes",
        unit=None,
        round_digits=None,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.DURATION,
        max_value=None,
        dict_data=None
    ),
    PolestarSensorDescription(
        key="model_name",
        name="Model name",
        query="getConsumerCarsV2",
        field_name="content/model/name",
        unit=None,
        round_digits=None,
        max_value=None,
        dict_data=None
    ),
    PolestarSensorDescription(
        key="last_updated",
        name="Last updated",
        query="getOdometerData",
        field_name="eventUpdatedTimestamp/iso",
        unit=None,
        round_digits=None,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.TIMESTAMP,
        max_value=None,
        dict_data=None
    ),
    PolestarSensorDescription(
        key="estimate_full_charge_range_miles",
        name="Calc. miles Full Charge",
        icon="mdi:map-marker-distance",
        query="getBatteryData",
        field_name="estimatedDistanceToEmptyMiles",
        unit='miles',
        round_digits=None,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.DISTANCE,
        max_value=None,
        dict_data=None
    ),
    PolestarSensorDescription(
        key="estimate_full_charge_range",
        name="Calc. km Full Charge",
        icon="mdi:map-marker-distance",
        query="getBatteryData",
        field_name="estimatedDistanceToEmptyKm",
        unit='km',
        round_digits=None,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.DISTANCE,
        max_value=None,
        dict_data=None
    ),
    PolestarSensorDescription(
        key="api_status_code",
        name="API status",
        icon="mdi:heart",
        query=None,
        field_name=None,
        unit=None,
        round_digits=None,
        max_value=None,
        dict_data=API_STATUS_DICT
    ),

)


async def async_setup_platform(
        hass: HomeAssistant,
        config: ConfigEntry,
        async_add_entities: AddEntitiesCallback,
        discovery_info=None):
    pass


async def async_setup_entry(
        hass: HomeAssistant,
        entry: ConfigEntry,
        async_add_entities: AddEntitiesCallback):
    """Set up using config_entry."""
    # get the device
    device: Polestar
    device = hass.data[POLESTAR_API_DOMAIN][entry.entry_id]

    # put data in cache
    await device.async_update()

    sensors = [
        PolestarSensor(device, description) for description in POLESTAR_SENSOR_TYPES
    ]
    async_add_entities(sensors)
    platform = entity_platform.current_platform.get()


class PolestarSensor(PolestarEntity, SensorEntity):
    """Representation of a Polestar Sensor."""

    entity_description: PolestarSensorDescription

    def __init__(self,
                 device: Polestar,
                 description: PolestarSensorDescription) -> None:
        """Initialize the sensor."""
        super().__init__(device)
        self._device = device
        # get the last 4 character of the id
        unique_id = device.vin[-4:]
        self.entity_id = f"{POLESTAR_API_DOMAIN}.'polestar_'.{unique_id}_{description.key}"
        self._attr_name = f"{description.name}"
        self._attr_unique_id = f"polestar_{unique_id}-{description.key}"
        self.description = description

        self.entity_description = description
        if description.state_class is not None:
            self._attr_state_class = description.state_class
        if description.device_class is not None:
            self._attr_device_class = description.device_class
        if self._device is not None and self._device.get_latest_call_code() == 200:
            self._async_update_attrs()

    def _get_current_value(self) -> StateType | None:
        """Get the current value."""
        return self.async_update()

    def get_skip_cache(self) -> bool:
        """Get the skip cache."""
        return self.description.key in ('vin', 'registration_number', 'model_name')

    @callback
    def _async_update_attrs(self) -> None:
        """Update the state and attributes."""
        self._attr_native_value = self._device.get_value(
            self.description.query, self.description.field_name, self.get_skip_cache())

    @property
    def unique_id(self) -> str:
        """Return a unique ID."""
        return f"{self._device.id}-{self.entity_description.key}"

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        return self._attr_name

    @property
    def icon(self) -> str | None:
        """Return the icon of the sensor."""
        return self.entity_description.icon

    @property
    def native_value(self) -> StateType:
        """Return the state of the sensor."""
        if self.entity_description.round_digits is not None:
            return round(self.state, self.entity_description.round_digits)
        return round(self.state, 2)

    @property
    def native_unit_of_measurement(self) -> str | None:
        """Return the unit the value is expressed in."""
        return self.entity_description.unit

    @property
    def state(self) -> StateType:
        """Return the state of the sensor."""
        if self.entity_description.dict_data is not None:
            # exception for api_status_code
            if self.entity_description.key == 'api_status_code':
                return self.entity_description.dict_data.get(self._device.get_latest_call_code(), "Error")
            return self.entity_description.dict_data.get(
                self._attr_native_value, self._attr_native_value)

        if self._attr_native_value != 0 and self._attr_native_value in (None, False):
            return None

        # battery charge level contain ".0" at the end, this should be removed
        if self.entity_description.key == 'battery_charge_level':
            if isinstance(self._attr_native_value, str):
                self._attr_native_value = int(
                    self._attr_native_value.replace('.0', ''))

        # prevent exponentianal value, we only give state value that is lower than the max value
        if self.entity_description.max_value is not None:
            if isinstance(self._attr_native_value, str):
                self._attr_native_value = int(self._attr_native_value)
            if self._attr_native_value > self.entity_description.max_value:
                return None

        # Custom state for estimated_fully_charged_time
        if self.entity_description.key == 'estimated_fully_charged_time':
            value = int(self._attr_native_value)
            if value > 0:
                return datetime.now().replace(second=0, microsecond=0) + timedelta(minutes=round(value))
            return 'Not charging'

        # round the value
        if self.entity_description.round_digits is not None:
            # if the value is integer, remove the decimal
            if self.entity_description.round_digits == 0 and isinstance(self._attr_native_value, int):
                return int(self._attr_native_value)
            return round(float(self._attr_native_value), self.entity_description.round_digits)

        if self.entity_description.key in ('estimate_full_charge_range', 'estimate_full_charge_range_miles'):
            battery_level = self._device.get_latest_data(
                self.entity_description.query, 'batteryChargeLevelPercentage')
            estimate_range = self._device.get_latest_data(
                self.entity_description.query, self.entity_description.field_name)

            if battery_level is None or estimate_range is None:
                return None

            if battery_level is False or estimate_range is False:
                return None

            battery_level = int(battery_level)
            estimate_range = int(estimate_range)

            estimate_range = round(estimate_range / battery_level * 100)

            return estimate_range

        if self.entity_description.key in 'current_odometer_meters' and int(self._attr_native_value) > 1000:
            self._attr_native_value = int(self._attr_native_value)
            km = round(self._attr_native_value / 1000,
                       self.entity_description.round_digits if self.entity_description.round_digits is not None else 0)

            return km

        return self._attr_native_value

    @property
    def unit_of_measurement(self) -> str:
        """Return the unit of measurement."""
        return self.entity_description.unit

    async def async_update(self) -> None:
        """Get the latest data and updates the states."""
        await self._device.async_update()
        self._attr_native_value = self._device.get_value(
            self.description.query, self.description.field_name, self.get_skip_cache())
