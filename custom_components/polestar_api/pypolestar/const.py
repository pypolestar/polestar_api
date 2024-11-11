"""Constants for Polestar."""

CACHE_TIME = 30

CAR_INFO_DATA = "getConsumerCarsV2"
ODO_METER_DATA = "getOdometerData"
BATTERY_DATA = "getBatteryData"
HEALTH_DATA = "getHealthData"

HTTPX_TIMEOUT = 30
TOKEN_REFRESH_WINDOW_MIN = 300

OIDC_PROVIDER_BASE_URL = "https://polestarid.eu.polestar.com"
OIDC_REDIRECT_URI = "https://www.polestar.com/sign-in-callback"
OIDC_CLIENT_ID = "l3oopkc_10"

API_AUTH_URL = "https://pc-api.polestar.com/eu-north-1/auth/"

BASE_URL = "https://pc-api.polestar.com/eu-north-1/my-star/"
BASE_URL_V2 = "https://pc-api.polestar.com/eu-north-1/mystar-v2/"
