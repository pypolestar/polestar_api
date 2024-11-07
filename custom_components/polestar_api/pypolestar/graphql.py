import httpx
from gql import Client
from gql.transport.httpx import HTTPXAsyncTransport

from .const import HTTPX_TIMEOUT


class _HTTPXAsyncTransport(HTTPXAsyncTransport):
    """GraphQL HTTPXAsyncTransport with pre-existing httpx client"""

    def __init__(self, *args, **kwargs):
        client = kwargs.pop("client")
        super().__init__(*args, **kwargs)
        self.client = client

    async def connect(self):
        pass

    async def close(self):
        pass


async def get_gql_client(client: httpx.AsyncClient, url: str) -> Client:
    transport = _HTTPXAsyncTransport(url=url, client=client)
    return Client(
        transport=transport,
        fetch_schema_from_transport=False,
        execute_timeout=HTTPX_TIMEOUT,
    )
