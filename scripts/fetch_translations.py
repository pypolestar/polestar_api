"""Fetch and update translations Crowdin"""

import io
import logging
import os
import time
from urllib.parse import urljoin
from zipfile import ZipFile

import httpx

BASE_URL = "https://api.crowdin.com"
PROJECT_ID = os.environ.get("CROWDIN_PROJECT_ID")
ACCESS_TOKEN = os.environ["CROWDIN_TOKEN"]


def get_translations(client: httpx.Client, access_token: str) -> bytes:
    """Request translations and return ZIP file contents"""

    auth_headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"}

    url = urljoin(BASE_URL, f"/api/v2/projects/{PROJECT_ID}/translations/builds")
    res = client.post(url, headers=auth_headers)
    res.raise_for_status()

    translation_id = res.json()["data"]["id"]

    url = urljoin(
        BASE_URL, f"/api/v2/projects/{PROJECT_ID}/translations/builds/{translation_id}"
    )
    wait = 1.0
    retries = 10

    while True:
        logging.info("Waiting for build to complete (retry in %.1f seconds)", wait)
        time.sleep(wait)
        res = client.get(url, headers=auth_headers)
        res.raise_for_status()

        if res.json()["data"]["status"] == "finished":
            break

        retries -= 1
        if not retries:
            raise TimeoutError("Timeout fetching build results")

    url = urljoin(
        BASE_URL,
        f"/api/v2/projects/{PROJECT_ID}/translations/builds/{translation_id}/download",
    )
    res = client.get(url, headers=auth_headers)
    res.raise_for_status()

    zip_url = res.json()["data"]["url"]
    res = client.get(zip_url)
    res.raise_for_status()

    return res.content


def main() -> None:
    """Main function."""

    logging.basicConfig(level=logging.INFO)

    client = httpx.Client()

    zip_buffer = io.BytesIO(get_translations(client, access_token=ACCESS_TOKEN))
    with ZipFile(zip_buffer, "r") as zip_file:
        zip_file.extractall(".")


if __name__ == "__main__":
    main()
