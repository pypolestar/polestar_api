from dataclasses import dataclass

from homeassistant.config_entries import ConfigEntry
from homeassistant.loader import Integration

from .polestar import PolestarCar, PolestarCoordinator

type PolestarConfigEntry = ConfigEntry[PolestarData]


@dataclass
class PolestarData:
    coordinator: PolestarCoordinator
    cars: list[PolestarCar]
    integration: Integration
