"""Support for Polestar sensors."""
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging
from typing import Final

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    UnitOfElectricCurrent,
    UnitOfLength,
    UnitOfPower,
    UnitOfSpeed,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_platform
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType
from homeassistant.util.unit_conversion import DistanceConverter

from . import DOMAIN as POLESTAR_API_DOMAIN
from .entity import PolestarEntity
from .polestar import Polestar

_LOGGER = logging.getLogger(__name__)
SCAN_INTERVAL = timedelta(seconds=15)


@dataclass
class PolestarSensorDescriptionMixin:
    """Define an entity description mixin for sensor entities."""

    query: str
    field_name: str
    round_digits: int | None
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
    "CHARGER_CONNECTION_STATUS_FAULT": "Fault",
    "CHARGER_CONNECTION_STATUS_UNSPECIFIED": "Unspecified"

}

CHARGING_STATUS_DICT = {
    "CHARGING_STATUS_DONE": "Done",
    "CHARGING_STATUS_IDLE": "Idle",
    "CHARGING_STATUS_CHARGING": "Charging",
    "CHARGING_STATUS_FAULT": "Fault",
    "CHARGING_STATUS_UNSPECIFIED": "Unspecified",
    "CHARGING_STATUS_SCHEDULED": "Scheduled",
    "CHARGING_STATUS_DISCHARGING": "Discharging",
    "CHARGING_STATUS_ERROR": "Error",
    "CHARGING_STATUS_SMART_CHARGING": "Smart Charging",


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
        key="estimate_range",
        name="Range",
        icon="mdi:map-marker-distance",
        query="getBatteryData",
        field_name="estimatedDistanceToEmptyKm",
        native_unit_of_measurement=UnitOfLength.KILOMETERS,
        round_digits=2,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.DISTANCE,
        max_value=660,
        dict_data=None
    ),
    # deprecated
#    PolestarSensorDescription(
#        key="estimate_distance_to_empty_miles",
#        name="Distance Miles Remaining",
#        icon="mdi:map-marker-distance",
#        query="getBatteryData",
#        field_name="estimatedDistanceToEmptyMiles",
#        native_unit_of_measurement=UnitOfLength.MILES,
#        round_digits=None,
#        state_class=SensorStateClass.MEASUREMENT,
#        device_class=SensorDeviceClass.DISTANCE,
#        max_value=410,
#        dict_data=None,
#    ),
    PolestarSensorDescription(
        key="current_odometer",
        name="Odometer",
        icon="mdi:map-marker-distance",
        query="getOdometerData",
        field_name="odometerMeters",
        native_unit_of_measurement=UnitOfLength.METERS,
        round_digits=2,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.DISTANCE,
        max_value=1000000,
        dict_data=None
    ),
    PolestarSensorDescription(
        key="average_speed",
        name="Avg. Speed",
        icon="mdi:speedometer",
        query="getOdometerData",
        field_name="averageSpeedKmPerHour",
        native_unit_of_measurement=UnitOfSpeed.KILOMETERS_PER_HOUR,
        round_digits=None,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.DISTANCE,
        max_value=150,
        dict_data=None
    ),
    PolestarSensorDescription(
        key="current_trip_meter_automatic",
        name="Trip Meter Automatic",
        icon="mdi:map-marker-distance",
        query="getOdometerData",
        field_name="tripMeterAutomaticKm",
        native_unit_of_measurement=UnitOfLength.KILOMETERS,
        round_digits=2,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.DISTANCE,
        max_value=100000,
        dict_data=None
    ),
    PolestarSensorDescription(
        key="current_trip_meter_manual",
        name="Trip Meter Manual",
        icon="mdi:map-marker-distance",
        query="getOdometerData",
        field_name="tripMeterManualKm",
        native_unit_of_measurement=UnitOfLength.KILOMETERS,
        round_digits=2,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.DISTANCE,
        max_value=100000,
        dict_data=None
    ),
    PolestarSensorDescription(
        key="battery_charge_level",
        name="Battery Level",
        query="getBatteryData",
        field_name="batteryChargeLevelPercentage",
        native_unit_of_measurement=PERCENTAGE,
        round_digits=0,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.BATTERY,
        max_value=100,
        dict_data=None
    ),
    PolestarSensorDescription(
        key="estimated_charging_time_to_full",
        name="Charging Time",
        icon="mdi:battery-clock",
        query="getBatteryData",
        field_name="estimatedChargingTimeToFullMinutes",
        native_unit_of_measurement=UnitOfTime.MINUTES,
        round_digits=None,
        max_value=1500,
        dict_data=None
    ),
    PolestarSensorDescription(
        key="charging_status",
        name="Charging Status",
        icon="mdi:ev-station",
        query="getBatteryData",
        field_name="chargingStatus",
        native_unit_of_measurement=None,
        round_digits=None,
        max_value=None,
        dict_data=CHARGING_STATUS_DICT
    ),
    PolestarSensorDescription(
        key="charging_power",
        name="Charging Power",
        icon="mdi:lightning-bolt",
        query="getBatteryData",
        field_name="chargingPowerWatts",
        native_unit_of_measurement=UnitOfPower.WATT,
        round_digits=None,
        max_value=None,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.POWER,
        dict_data=None
    ),
    PolestarSensorDescription(
        key="charging_current",
        name="Charging Current",
        icon="mdi:current-ac",
        query="getBatteryData",
        field_name="chargingCurrentAmps",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        round_digits=None,
        max_value=None,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.POWER,
        dict_data=None
    ),
    PolestarSensorDescription(
        key="charger_connection_status",
        name="Charging Connection Status",
        icon="mdi:connection",
        query="getBatteryData",
        field_name="chargerConnectionStatus",
        native_unit_of_measurement=None,
        round_digits=None,
        max_value=None,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=None,
        dict_data=CHARGING_CONNECTION_STATUS_DICT
    ),
    PolestarSensorDescription(
        key="average_energy_consumption_kwh_per_100",
        name="Avg. Energy Consumption",
        icon="mdi:battery-clock",
        query="getBatteryData",
        field_name="averageEnergyConsumptionKwhPer100Km",
        native_unit_of_measurement='kWh/100km',
        round_digits=None,
        max_value=None,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=None,
        dict_data=None
    ),
    PolestarSensorDescription(
        key="estimated_charging_time_minutes_to_target_distance",
        name="Estimated Charging Time To Target Distance",
        icon="mdi:battery-clock",
        query="getBatteryData",
        field_name="estimatedChargingTimeMinutesToTargetDistance",
        native_unit_of_measurement=PERCENTAGE,
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
        native_unit_of_measurement=None,
        round_digits=None,
        max_value=None,
        dict_data=None
    ),
    PolestarSensorDescription(
        key="software_version",
        name="Software Version",
        icon="mdi:information-outline",
        query="getConsumerCarsV2",
        field_name="software/version",
        native_unit_of_measurement=None,
        round_digits=None,
        max_value=None,
        dict_data=None
    ),
    PolestarSensorDescription(
        key="registration_number",
        name="Registration Number",
        icon="mdi:numeric-1-box",
        query="getConsumerCarsV2",
        field_name="registrationNo",
        native_unit_of_measurement=None,
        round_digits=None,
        max_value=None,
        dict_data=None
    ),
    PolestarSensorDescription(
        key="estimated_fully_charged_time",
        name="Time Full Charged",
        icon="mdi:battery-clock",
        query="getBatteryData",
        field_name="estimatedChargingTimeToFullMinutes",
        native_unit_of_measurement=None,
        round_digits=None,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.DURATION,
        max_value=None,
        dict_data=None
    ),
    PolestarSensorDescription(
        key="model_name",
        name="Model Name",
        icon="mdi:car-electric",
        query="getConsumerCarsV2",
        field_name="content/model/name",
        native_unit_of_measurement=None,
        round_digits=None,
        max_value=None,
        dict_data=None
    ),
    PolestarSensorDescription(
        key="last_updated_odometer_data",
        name="Last Updated Odometer Data",
        icon="mdi:clock",
        query="getOdometerData",
        field_name="eventUpdatedTimestamp/iso",
        native_unit_of_measurement=None,
        round_digits=None,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.TIMESTAMP,
        max_value=None,
        dict_data=None
    ),
    PolestarSensorDescription(
        key="last_updated_battery_data",
        name="Last Updated Battery Data",
        icon="mdi:clock",
        query="getBatteryData",
        field_name="eventUpdatedTimestamp/iso",
        native_unit_of_measurement=None,
        round_digits=None,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.TIMESTAMP,
        max_value=None,
        dict_data=None
    ),
    PolestarSensorDescription(
        key="estimate_full_charge_range",
        name="Calc. Full Charge Range",
        icon="mdi:map-marker-distance",
        query="getBatteryData",
        field_name="estimatedDistanceToEmptyKm",
        native_unit_of_measurement=UnitOfLength.KILOMETERS,
        round_digits=2,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.DISTANCE,
        max_value=660, # WLTP range max 655
        dict_data=None
    ),
    PolestarSensorDescription(
        key="api_status_code",
        name="API Status",
        icon="mdi:heart",
        query=None,
        field_name=None,
        native_unit_of_measurement=None,
        round_digits=None,
        max_value=None,
        dict_data=API_STATUS_DICT
    ),
    PolestarSensorDescription(
        key="api_token_expires_at",
        name="API Token Expired At",
        icon="mdi:heart",
        query=None,
        field_name=None,
        native_unit_of_measurement=None,
        round_digits=None,
        max_value=None,
        dict_data=None
    ),

)


async def async_setup_platform(
        hass: HomeAssistant,
        config: ConfigEntry,
        async_add_entities: AddEntitiesCallback,
        discovery_info=None):
    """Set up the Polestar sensor."""
    pass


async def async_setup_entry(
        hass: HomeAssistant,
        entry: ConfigEntry,
        async_add_entities: AddEntitiesCallback):
    """Set up using config_entry."""
    # get the device
    device: Polestar
    device = hass.data[POLESTAR_API_DOMAIN][entry.entry_id]
    await device.init()

    # put data in cache
    await device.async_update()

    sensors = [
        PolestarSensor(device, description) for description in POLESTAR_SENSOR_TYPES
    ]
    async_add_entities(sensors)
    entity_platform.current_platform.get()


class PolestarSensor(PolestarEntity, SensorEntity):
    """Representation of a Polestar Sensor."""

    entity_description: PolestarSensorDescription
    attr_has_entity_name = True

    def __init__(self,
                 device: Polestar,
                 description: PolestarSensorDescription) -> None:
        """Initialize the sensor."""
        super().__init__(device)
        self._device = device
        # get the last 4 character of the id
        unique_id = device.vin[-4:]
        self.entity_id = f"{POLESTAR_API_DOMAIN}.'polestar_'.{unique_id}_{description.key}"
        #self._attr_name = f"{description.name}"
        self._attr_unique_id = f"polestar_{unique_id}-{description.key}"
        self.entity_description = description
        self.attr_translation_key = f"polestar_{description.key}"
        self._attr_native_unit_of_measurement = description.native_unit_of_measurement
        self._sensor_data = None
        self._attr_unit_of_measurement = description.native_unit_of_measurement
        self._attr_native_value = self._device.get_value(
            self.entity_description.query, self.entity_description.field_name, self.get_skip_cache())

        if description.round_digits is not None:
            self.attr_suggested_display_precision = description.round_digits

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
        return self.entity_description.key in ('vin', 'registration_number', 'model_name')

    @callback
    def _async_update_attrs(self) -> None:
        """Update the state and attributes."""
        self._sensor_data= self._device.get_value(
            self.entity_description.query, self.entity_description.field_name, self.get_skip_cache())

    @property
    def icon(self) -> str | None:
        """Return the icon of the sensor."""
        return self.entity_description.icon

    @property
    def state(self) -> StateType:
        """Return the state of the sensor."""
        if self._attr_native_value is None and self.entity_description.key in ('charging_current', 'charging_power', 'estimated_charging_time_minutes_to_target_distance'):
            #self.entity_description.native_unit_of_measurement = None
            self._attr_native_unit_of_measurement = None
            return "Not Supported Yet"

        if self.entity_description.dict_data is not None:
            # exception for api_status_code
            if self.entity_description.key == 'api_status_code':
                return self.entity_description.dict_data.get(self._device.get_latest_call_code(), "Error")
            self._attr_native_value  =  self.entity_description.dict_data.get(
                self._attr_native_value, self._attr_native_value)

        if self.entity_description.key == 'api_token_expires_at':
            if self._device.get_token_expiry() is None:
                return None
            return self._device.get_token_expiry().strftime("%Y-%m-%d %H:%M:%S")
        if self._attr_native_value != 0 and self._attr_native_value in (None, False):
            return None

        if self.entity_description.key in ('estimate_full_charge_range'):
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

            self._sensor_data = round(estimate_range / battery_level * 100)

        # Custom state for estimated_fully_charged_time
        if self.entity_description.key == 'estimated_fully_charged_time':
            value = int(self._attr_native_value)
            if value > 0:
                return datetime.now().replace(second=0, microsecond=0) + timedelta(minutes=round(value))
            return 'Not charging'

        # if GUI changed the unit, we need to convert the value
        if self._sensor_option_unit_of_measurement is not None:
            if self._sensor_option_unit_of_measurement in (UnitOfLength.MILES, UnitOfLength.KILOMETERS, UnitOfLength.METERS):
                    self._attr_native_value = DistanceConverter.convert(
                        self._sensor_data, self.entity_description.native_unit_of_measurement, self._sensor_option_unit_of_measurement
                    )
                    self._attr_native_unit_of_measurement = self._sensor_option_unit_of_measurement
        if self.entity_description.key in ("estimate_range", "estimate_full_charge_range"):
            if self._sensor_option_unit_of_measurement ==  UnitOfLength.MILES:
                self.entity_description.max_value = 410
            elif self._sensor_option_unit_of_measurement ==  UnitOfLength.KILOMETERS:
                self.entity_description.max_value = 660
            elif self._sensor_option_unit_of_measurement ==  UnitOfLength.METERS:
                self.entity_description.max_value = 660000

        # prevent exponentianal value, we only give state value that is lower than the max value
        if self.entity_description.max_value is not None:
            if isinstance(self._attr_native_value, str):
                self._attr_native_value = int(self._attr_native_value)
            if self._attr_native_value > self.entity_description.max_value:
                _LOGGER.warning("%s: Value %s is higher than max value %s", self.entity_description.key, self._attr_native_value, self.entity_description.max_value)
                return None
        # round the value
        if self.entity_description.round_digits is not None:
            # if the value is integer, remove the decimal
            if self.entity_description.round_digits == 0 and isinstance(self._attr_native_value, int):
                self._attr_native_value =  int(self._attr_native_value)
            self._attr_native_value = round(float(self._attr_native_value), self.entity_description.round_digits)

        return self._attr_native_value

    @property
    def unit_of_measurement(self) -> str:
        """Return the unit of measurement."""
        return self.native_unit_of_measurement

    async def async_update(self) -> None:
        """Get the latest data and updates the states."""
        try:
            await self._device.async_update()
            value = self._device.get_value(
                self.entity_description.query, self.entity_description.field_name, self.get_skip_cache())

            if value is not None:
                self._attr_native_value = value
        except Exception:
            _LOGGER.warning("Failed to update sensor async update")
            self._device.polestarApi.next_update = datetime.now() + timedelta(seconds=60)

