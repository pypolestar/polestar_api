"""Constants for the Polestar API integration."""

from datetime import timedelta

DOMAIN = "polestar_api"
TIMEOUT = 90

CACHE_TIME = 600
DEFAULT_SCAN_INTERVAL = timedelta(seconds=60)

CONF_VIN = Final = "vin"
