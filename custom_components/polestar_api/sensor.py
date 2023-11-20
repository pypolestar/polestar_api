from datetime import datetime, timedelta
import logging
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


from .polestar import PolestarApi

from homeassistant.const import (
    PERCENTAGE,
)


_LOGGER = logging.getLogger(__name__)
SCAN_INTERVAL = timedelta(seconds=15)


@dataclass
class PolestarSensorDescriptionMixin:
    """Define an entity description mixin for sensor entities."""

    path: str
    unit: str
    round_digits: int | None
    unit: str | None
    response_path: str | None
    max_value: int | None


@dataclass
class PolestarSensorDescription(
    SensorEntityDescription,  PolestarSensorDescriptionMixin
):
    """Class to describe an Polestar sensor entity."""


ChargingConnectionStatusDict = {
    "CONNECTION_STATUS_DISCONNECTED": "Disconnected",
    "CONNECTION_STATUS_CONNECTED_AC": "Connected AC",
    "CONNECTION_STATUS_CONNECTED_DC": "Connected DC",
    "CONNECTION_STATUS_UNSPECIFIED": "Unspecified",
}

ChargingSystemStatusDict = {
    "CHARGING_SYSTEM_UNSPECIFIED": "Unspecified",
    "CHARGING_SYSTEM_CHARGING": "Charging",
    "CHARGING_SYSTEM_IDLE": "Idle",
    "CHARGING_SYSTEM_FAULT": "Fault",
}


POLESTAR_SENSOR_TYPES: Final[tuple[PolestarSensorDescription, ...]] = (
    PolestarSensorDescription(
        key="estimate_full_charge_range",
        name="Est. full charge range",
        icon="mdi:map-marker-distance",
        path="{vin}/recharge-status",
        response_path=None,
        unit='km',
        round_digits=None,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.DISTANCE,
        max_value=None
    ),
    PolestarSensorDescription(
        key="estimate_full_charge_range_miles",
        name="Est. full charge range",
        icon="mdi:map-marker-distance",
        path="{vin}/recharge-status",
        response_path=None,
        unit='miles',
        round_digits=None,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.DISTANCE,
        max_value=None
    ),
    PolestarSensorDescription(
        key="battery_charge_level",
        name="Battery level",
        path="{vin}/recharge-status",
        response_path="batteryChargeLevel.value",
        unit=PERCENTAGE,
        round_digits=0,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.BATTERY,
        max_value=None,
    ),
    PolestarSensorDescription(
        key="last_updated",
        name="Last updated",
        path="{vin}/recharge-status",
        response_path="batteryChargeLevel.timestamp",
        unit=None,
        round_digits=None,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.TIMESTAMP,
        max_value=None,
    ),
    PolestarSensorDescription(
        key="electric_range",
        name="EV Range",
        icon="mdi:map-marker-distance",
        path="{vin}/recharge-status",
        response_path="electricRange.value",
        unit='km',
        round_digits=None,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.DISTANCE,
        max_value=570,  # prevent spike value, and this should be the max range of polestar
    ),
    PolestarSensorDescription(
        key="electric_range_miles",
        name="EV Range",
        icon="mdi:map-marker-distance",
        path="{vin}/recharge-status",
        response_path="electricRange.value",
        unit='miles',
        round_digits=None,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.DISTANCE,
        max_value=355,  # prevent spike value, and this should be the max range of polestar
    ),
    PolestarSensorDescription(
        key="estimated_charging_time",
        name="Charging time",
        icon="mdi:battery-clock",
        path="{vin}/recharge-status",
        response_path="estimatedChargingTime.value",
        unit='Minutes',
        round_digits=None,
        max_value=None,
    ),
    PolestarSensorDescription(
        key="estimated_fully_charged_time",
        name="Fully charged time",
        icon="mdi:battery-clock",
        path="{vin}/recharge-status",
        response_path="estimatedChargingTime.value",
        unit=None,
        round_digits=None,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.DURATION,
        max_value=None,
    ),
    PolestarSensorDescription(
        key="charging_connection_status",
        name="Charg. connection status",
        icon="mdi:car",
        path="{vin}/recharge-status",
        response_path="chargingConnectionStatus.value",
        unit=None,
        round_digits=None,
        state_class=SensorStateClass.MEASUREMENT,
        max_value=None,
    ),
    PolestarSensorDescription(
        key="charging_system_status",
        name="Charg. system status",
        icon="mdi:car",
        path="{vin}/recharge-status",
        response_path="chargingSystemStatus.value",
        unit=None,
        round_digits=None,
        max_value=None,
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
    device: PolestarApi
    device = hass.data[POLESTAR_API_DOMAIN][entry.entry_id]
    # put data in cache
    await device.get_data("{vin}/recharge-status")

    sensors = [
        PolestarSensor(device, description) for description in POLESTAR_SENSOR_TYPES
    ]
    async_add_entities(sensors)
    platform = entity_platform.current_platform.get()


class PolestarSensor(PolestarEntity, SensorEntity):
    """Representation of a Polestar Sensor."""

    entity_description: PolestarSensorDescription

    def __init__(self,
                 device: PolestarApi,
                 description: PolestarSensorDescription) -> None:
        """Initialize the sensor."""
        super().__init__(device)
        self._device = device
        # get the last 4 character of the id
        unique_id = device.vin[-4:]
        self.entity_id = f"{POLESTAR_API_DOMAIN}.'polestar_'.{unique_id}_{description.key}"
        self._attr_name = f"{description.name}"
        self._attr_unique_id = f"polestar_{unique_id}-{description.key}"
        self.value = None
        self.description = description

        self.entity_description = description
        if description.state_class is not None:
            self._attr_state_class = description.state_class
        if description.device_class is not None:
            self._attr_device_class = description.device_class
        self._async_update_attrs()

    def _get_current_value(self) -> StateType | None:
        """Get the current value."""
        return self.async_update()

    @callback
    def _async_update_attrs(self) -> None:
        """Update the state and attributes."""
        # try to fill the current cache data
        self._attr_native_value = self._device.get_cache_data(
            self.description.path, self.description.response_path)

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
        return round(self.state, 2)

    @property
    def native_unit_of_measurement(self) -> str | None:
        """Return the unit the value is expressed in."""
        return self.entity_description.unit

    @property
    def state(self) -> StateType:
        """Return the state of the sensor."""
        if self._attr_native_value is None:
            return None

        # parse the long text with a shorter one from the dict
        if self.entity_description.key == 'charging_connection_status':
            return ChargingConnectionStatusDict.get(self._attr_native_value, self._attr_native_value)
        if self.entity_description.key == 'charging_system_status':
            return ChargingSystemStatusDict.get(self._attr_native_value, self._attr_native_value)

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
                self.entity_description.path, 'batteryChargeLevel.value')
            estimate_range = self._device.get_latest_data(
                self.entity_description.path, 'electricRange.value')

            if battery_level is None or estimate_range is None:
                return None

            if battery_level is False or estimate_range is False:
                return None

            battery_level = int(battery_level.replace('.0', ''))
            estimate_range = int(estimate_range)

            estimate_range = round(estimate_range / battery_level * 100)

            if self.entity_description.key == 'estimate_full_charge_range_miles':
                return round(estimate_range / 1.609344, self.entity_description.round_digits if self.entity_description.round_digits is not None else 0)

            return estimate_range

        if self.entity_description.key == 'electric_range_miles':
            if self._attr_native_value is None:
                return None

            if self._attr_native_value is False:
                return None

            self._attr_native_value = int(self._attr_native_value)
            miles = round(self._attr_native_value / 1.609344,
                          self.entity_description.round_digits if self.entity_description.round_digits is not None else 0)

            return miles
        return self._attr_native_value

    @property
    def unit_of_measurement(self) -> str:
        """Return the unit of measurement."""
        return self.entity_description.unit

    async def async_update(self) -> None:
        """Get the latest data and updates the states."""
        data = await self._device.get_data(self.entity_description.path, self.entity_description.response_path)
        if data is None:
            return

        self._attr_native_value = data
        self.value = data
