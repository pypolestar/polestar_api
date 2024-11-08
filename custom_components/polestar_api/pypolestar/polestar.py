"""Asynchronous Python client for the Polestar API.""" ""

import logging
import threading
import time
from collections import defaultdict
from datetime import datetime, timedelta

import httpx
from gql.transport.exceptions import TransportQueryError
from graphql import DocumentNode

from .auth import PolestarAuth
from .const import (
    BASE_URL,
    BASE_URL_V2,
    BATTERY_DATA,
    CACHE_TIME,
    CAR_INFO_DATA,
    ODO_METER_DATA,
)
from .exception import (
    PolestarApiException,
    PolestarAuthException,
    PolestarNoDataException,
    PolestarNotAuthorizedException,
)
from .graphql import (
    QUERY_GET_BATTERY_DATA,
    QUERY_GET_CONSUMER_CARS_V2,
    QUERY_GET_ODOMETER_DATA,
    get_gql_client,
)

_LOGGER = logging.getLogger(__name__)


class PolestarApi:
    """Main class for handling connections with the Polestar API."""

    def __init__(
        self,
        username: str,
        password: str,
        client_session: httpx.AsyncClient | None = None,
        vins: list[str] | None = None,
        unique_id: str | None = None,
    ) -> None:
        """Initialize the Polestar API."""
        self.client_session = client_session or httpx.AsyncClient()
        self.username = username
        self.auth = PolestarAuth(username, password, self.client_session, unique_id)
        self.updating = threading.Lock()
        self.latest_call_code = None
        self.latest_call_code_2 = None
        self.next_update = None
        self.car_data_by_vin: dict[str, dict] = {}
        self.cache_data_by_vin: dict[str, dict] = defaultdict(dict)
        self.cache_ttl = timedelta(seconds=CACHE_TIME)
        self.next_update_delay = timedelta(seconds=5)
        self.configured_vins = set(vins) if vins else None
        self.logger = _LOGGER.getChild(unique_id) if unique_id else _LOGGER

    async def async_init(self) -> None:
        """Initialize the Polestar API."""
        await self.auth.async_init()
        await self.auth.get_token()

        if self.auth.access_token is None:
            self.logger.warning("No access token %s", self.username)
            return

        if not (car_data := await self._get_vehicle_data()):
            self.logger.warning("No cars found for %s", self.username)
            return

        for data in car_data:
            vin = data["vin"]
            if self.configured_vins and vin not in self.configured_vins:
                continue
            self.car_data_by_vin[vin] = data
            self.cache_data_by_vin[vin][CAR_INFO_DATA] = {
                "data": self.car_data_by_vin[vin],
                "timestamp": datetime.now(),
            }
            self.logger.debug("API setup for VIN %s", vin)

    @property
    def vins(self) -> list[str]:
        return list(self.car_data_by_vin.keys())

    def get_latest_data(
        self, vin: str, query: str, field_name: str
    ) -> dict or bool or None:
        """Get the latest data from the Polestar API."""
        if self.cache_data_by_vin and self.cache_data_by_vin[vin][query]:
            data = self.cache_data_by_vin[vin][query]["data"]
            if data is None:
                return False
            return self._get_field_name_value(field_name, data)
        return None

    async def get_ev_data(self, vin: str) -> None:
        """
        Get the latest ev data from the Polestar API.

        Currently updates data for all VINs (this might change in the future).
        """

        if not self.updating.acquire(blocking=False):
            self.logger.debug("Skipping update, already in progress")
            return

        if self.next_update is not None and self.next_update > datetime.now():
            self.logger.debug("Skipping update, next update at %s", self.next_update)
            self.updating.release()
            return

        self.logger.debug("Starting update for VIN %s", vin)
        t1 = time.perf_counter()

        try:
            if self.auth.need_token_refresh():
                await self.auth.get_token(refresh=True)
        except PolestarAuthException as e:
            self._set_latest_call_code(BASE_URL, 500)
            self.logger.warning("Auth Exception: %s", str(e))
            self.updating.release()
            return

        async def call_api(func):
            try:
                await func()
            except PolestarNotAuthorizedException:
                await self.auth.get_token()
            except PolestarApiException as e:
                self._set_latest_call_code(BASE_URL_V2, 500)
                self.logger.warning("Failed to get %s data %s", func.__name__, str(e))

        try:
            await call_api(lambda: self._get_odometer_data(vin))
            await call_api(lambda: self._get_battery_data(vin))
            self.next_update = datetime.now() + self.next_update_delay
        finally:
            self.updating.release()

        t2 = time.perf_counter()
        self.logger.debug("Update took %.2f seconds", t2 - t1)

    def get_cache_data(
        self, vin: str, query: str, field_name: str, skip_cache: bool = False
    ) -> dict | None:
        """Get the latest data from the cache."""
        if query is None:
            return None
        self.logger.debug(
            "get_cache_data %s %s %s%s",
            vin,
            query,
            field_name,
            " (skip_cache)" if skip_cache else "",
        )
        if self.cache_data_by_vin and self.cache_data_by_vin[vin].get(query):
            cache_entry = self.cache_data_by_vin[vin][query]
            data = cache_entry["data"]
            if data is not None and (
                skip_cache is True
                or cache_entry["timestamp"] + self.cache_ttl > datetime.now()
            ):
                return self._get_field_name_value(field_name, data)
        return None

    @staticmethod
    def _get_field_name_value(field_name: str, data: dict) -> str or bool or None:
        if field_name is None or data is None:
            return None

        if "/" in field_name:
            field_names = field_name.split("/")
            for key in field_names:
                if isinstance(data, dict) and key in data:
                    data = data[key]
                else:
                    return None
            return data

        if isinstance(data, dict) and field_name in data:
            return data[field_name]

        return None

    async def _get_odometer_data(self, vin: str) -> None:
        """Get the latest odometer data from the Polestar API."""

        result = await self._query_graph_ql(
            url=BASE_URL_V2,
            query=QUERY_GET_ODOMETER_DATA,
            variable_values={"vin": vin},
        )

        self.cache_data_by_vin[vin][ODO_METER_DATA] = {
            "data": result[ODO_METER_DATA],
            "timestamp": datetime.now(),
        }

    async def _get_battery_data(self, vin: str) -> None:
        result = await self._query_graph_ql(
            url=BASE_URL_V2,
            query=QUERY_GET_BATTERY_DATA,
            variable_values={"vin": vin},
        )

        self.cache_data_by_vin[vin][BATTERY_DATA] = {
            "data": result[BATTERY_DATA],
            "timestamp": datetime.now(),
        }

    async def _get_vehicle_data(self) -> dict | None:
        """Get the latest vehicle data from the Polestar API."""
        result = await self._query_graph_ql(
            url=BASE_URL,
            query=QUERY_GET_CONSUMER_CARS_V2,
            variable_values={"locale": "en_GB"},
        )

        if result[CAR_INFO_DATA] is None or len(result[CAR_INFO_DATA]) == 0:
            self.logger.exception("No cars found in account")
            raise PolestarNoDataException("No cars found in account")

        return result[CAR_INFO_DATA]

    def _set_latest_call_code(self, url: str, code: int) -> None:
        if url == BASE_URL:
            self.latest_call_code = code
        else:
            self.latest_call_code_2 = code

    async def _query_graph_ql(
        self,
        url: str,
        query: DocumentNode,
        operation_name: str | None = None,
        variable_values: dict | None = None,
    ):
        self.logger.debug("GraphQL URL: %s", url)

        async with await get_gql_client(
            url=url,
            client=self.client_session,
        ) as client:
            try:
                result = await client.execute(
                    query,
                    operation_name=operation_name,
                    variable_values=variable_values,
                    extra_args={
                        "headers": {"Authorization": f"Bearer {self.auth.access_token}"}
                    },
                )
            except TransportQueryError as exc:
                self.logger.debug("GraphQL TransportQueryError: %s", str(exc))
                if (
                    exc.errors
                    and len(exc.errors)
                    and exc.errors[0]["extensions"]["code"] == "UNAUTHENTICATED"
                ):
                    self._set_latest_call_code(url, 401)
                    raise PolestarNotAuthorizedException(
                        exc.errors[0]["message"]
                    ) from exc
                self._set_latest_call_code(url, 500)
                raise PolestarApiException from exc
            except Exception as exc:
                self.logger.debug("GraphQL Exception: %s", str(exc))
                raise exc

        self.logger.debug("GraphQL Result: %s", result)
        self._set_latest_call_code(url, 200)

        return result
