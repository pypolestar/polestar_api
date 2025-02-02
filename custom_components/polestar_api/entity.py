"""Base class for Polestar entities."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING, Any, Callable

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import EntityDescription
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import ATTRIBUTION, DOMAIN
from .coordinator import PolestarCoordinator

if TYPE_CHECKING:
    from homeassistant.helpers.entity import EntityDescription

_LOGGER = logging.getLogger(__name__)


class PolestarEntityDataSource(StrEnum):
    INFORMATION = "car_information_data"
    ODOMETER = "car_odometer_data"
    BATTERY = "car_battery_data"
    HEALTH = "car_health_data"


class PolestarEntityDataSourceException(Exception):
    """Exception raised when requested data source/attribute is missing"""


@dataclass(frozen=True)
class PolestarEntityDescription(EntityDescription):
    """Describes a Polestar entity."""

    data_source: PolestarEntityDataSource | None = None
    data_attribute: str | None = None
    data_fn: Callable[[Any], Any] | None = None

    def __post_init__(self):
        """Validate the data source and attribute configuration."""
        if bool(self.data_source) != bool(self.data_attribute):
            raise ValueError(
                "Both data_source and data_attribute must be provided together"
            )


class PolestarEntity(CoordinatorEntity[PolestarCoordinator]):
    """Base class for Polestar entities."""

    _attr_attribution = ATTRIBUTION
    entity_description: PolestarEntityDescription

    def __init__(
        self,
        coordinator: PolestarCoordinator,
        entity_description: PolestarEntityDescription,
    ) -> None:
        """Initialize the Polestar entity."""
        super().__init__(coordinator)
        self.entity_description = entity_description
        self.entity_id = (
            f"{DOMAIN}.polestar_{coordinator.get_short_id()}_{entity_description.key}"
        )
        self._attr_unique_id = f"polestar_{coordinator.vin}_{entity_description.key}"
        self._attr_translation_key = f"polestar_{entity_description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self.coordinator.vin)},
            manufacturer="Polestar",
            model=self.coordinator.model,
            name=self.coordinator.name,
            serial_number=self.coordinator.vin,
        )

    def get_native_value(self) -> str | None:
        if (
            self.entity_description.data_source
            and self.entity_description.data_attribute
        ):
            if data := getattr(self.coordinator, self.entity_description.data_source):
                if not hasattr(data, self.entity_description.data_attribute):
                    _LOGGER.error(
                        "Invalid attribute %s.%s for entity %s",
                        self.entity_description.data_source,
                        self.entity_description.data_attribute,
                        self.entity_id,
                    )
                    return None

                if value := getattr(data, self.entity_description.data_attribute, None):
                    return (
                        self.entity_description.data_fn(value)
                        if self.entity_description.data_fn
                        else value
                    )
                else:
                    _LOGGER.debug(
                        "%s.%s not available for entity %s",
                        self.entity_description.data_source,
                        self.entity_description.data_attribute,
                        self.entity_id,
                    )
            else:
                _LOGGER.debug("%s not available", self.entity_description.data_source)

            return None
        raise PolestarEntityDataSourceException
