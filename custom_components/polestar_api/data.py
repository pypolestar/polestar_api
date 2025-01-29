from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.loader import Integration
    from pypolestar import PolestarApi

    from .coordinator import PolestarCoordinator


type PolestarConfigEntry = ConfigEntry[PolestarData]


@dataclass(frozen=True)
class PolestarData:
    api_client: PolestarApi
    coordinators: list[PolestarCoordinator]
    integration: Integration
