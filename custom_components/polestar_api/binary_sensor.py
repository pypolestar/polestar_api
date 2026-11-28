"""Support for Polestar binary sensors."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.const import EntityCategory

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
class PolestarBinarySensorEntityDescription(
    BinarySensorEntityDescription, PolestarEntityDescription
):
    """Class to describe an Polestar binary_sensor entity."""


def is_open(value: str) -> bool | None:
    """Open or ajar is on; closed is off; unspecified is unknown."""
    return {"Open": True, "Ajar": True, "Closed": False}.get(value)


def is_unlocked(value: str) -> bool | None:
    """HA lock device class: on means unlocked."""
    return {"Unlocked": True, "Locked": False}.get(value)


def any_light_failure(value: dict) -> bool | None:
    """On if any exterior light reports a failure; unknown if none report."""
    states = {str(v) for v in (value or {}).values()} - {"Unspecified"}
    return ("Failure" in states) if states else None


def _opening(key: str, attribute: str, device_class: BinarySensorDeviceClass):
    return PolestarBinarySensorEntityDescription(
        key=key,
        device_class=device_class,
        data_source=PolestarEntityDataSource.GRPC_EXTERIOR,
        data_state_attribute=attribute,
        data_state_fn=is_open,
    )


EXTERIOR_ENTITY_DESCRIPTIONS: Final[tuple[BinarySensorEntityDescription, ...]] = (
    PolestarBinarySensorEntityDescription(
        key="central_lock",
        device_class=BinarySensorDeviceClass.LOCK,
        data_source=PolestarEntityDataSource.GRPC_EXTERIOR,
        data_state_attribute="central_lock",
        data_state_fn=is_unlocked,
    ),
    PolestarBinarySensorEntityDescription(
        key="tailgate_lock",
        device_class=BinarySensorDeviceClass.LOCK,
        data_source=PolestarEntityDataSource.GRPC_EXTERIOR,
        data_state_attribute="tailgate_lock",
        data_state_fn=is_unlocked,
    ),
    _opening("front_left_door", "front_left_door", BinarySensorDeviceClass.DOOR),
    _opening("front_right_door", "front_right_door", BinarySensorDeviceClass.DOOR),
    _opening("rear_left_door", "rear_left_door", BinarySensorDeviceClass.DOOR),
    _opening("rear_right_door", "rear_right_door", BinarySensorDeviceClass.DOOR),
    _opening("front_left_window", "front_left_window", BinarySensorDeviceClass.WINDOW),
    _opening(
        "front_right_window", "front_right_window", BinarySensorDeviceClass.WINDOW
    ),
    _opening("rear_left_window", "rear_left_window", BinarySensorDeviceClass.WINDOW),
    _opening("rear_right_window", "rear_right_window", BinarySensorDeviceClass.WINDOW),
    _opening("hood", "hood", BinarySensorDeviceClass.OPENING),
    _opening("tailgate", "tailgate", BinarySensorDeviceClass.OPENING),
)

HEALTH_ENTITY_DESCRIPTIONS: Final[tuple[BinarySensorEntityDescription, ...]] = (
    PolestarBinarySensorEntityDescription(
        key="exterior_light_failure",
        device_class=BinarySensorDeviceClass.PROBLEM,
        data_source=PolestarEntityDataSource.GRPC_HEALTH,
        data_state_attribute="exterior_light_warnings",
        data_state_fn=any_light_failure,
    ),
)

ENTITY_DESCRIPTIONS: Final[tuple[BinarySensorEntityDescription, ...]] = (
    PolestarBinarySensorEntityDescription(
        key="api_connected",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    *EXTERIOR_ENTITY_DESCRIPTIONS,
    *HEALTH_ENTITY_DESCRIPTIONS,
)


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001 Unused function argument: `hass`
    entry: PolestarConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the binary_sensor platform."""
    async_add_entities(
        PolestarBinarySensor(
            coordinator=coordinator,
            entity_description=entity_description,
        )
        for coordinator in entry.runtime_data.coordinators
        for entity_description in ENTITY_DESCRIPTIONS
    )


class PolestarBinarySensor(PolestarEntity, BinarySensorEntity):
    """integration_blueprint binary_sensor class."""

    entity_description: PolestarBinarySensorEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: PolestarCoordinator,
        entity_description: PolestarBinarySensorEntityDescription,
    ) -> None:
        """Initialize the binary_sensor class."""
        super().__init__(coordinator, entity_description)

    @property
    def is_on(self) -> bool | None:
        """Return true if the binary_sensor is on."""
        try:
            return self.get_native_value()
        except PolestarEntityDataSourceException:
            return self.coordinator.data.get(self.entity_description.key)
