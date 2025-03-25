import io
import logging
import os
import time
from urllib.parse import urljoin
from zipfile import ZipFile

import httpx

BASE_URL = "https://api.crowdin.com"
PROJECT_ID = os.environ.get("CROWDIN_PROJECT_ID")
ACCESS_TOKEN = os.environ.get("CROWDIN_TOKEN")


def get_translations(client: httpx.Client) -> bytes:
    """Request translations and return ZIP file contents"""

    url = urljoin(BASE_URL, f"/api/v2/projects/{PROJECT_ID}/translations/builds")

    res = client.post(url)
    translation_id = res.json()["data"]["id"]

    url = urljoin(
        BASE_URL, f"/api/v2/projects/{PROJECT_ID}/translations/builds/{translation_id}"
    )
    while True:
        logging.info("Waiting for build to complete")
        time.sleep(1)
        res = client.get(url)
        if res.json()["data"]["status"] == "finished":
            break

    url = urljoin(
        BASE_URL,
        f"/api/v2/projects/{PROJECT_ID}/translations/builds/{translation_id}/download",
    )
    res = client.get(url)
    zip_url = res.json()["data"]["url"]

    res = httpx.get(zip_url)

    return res.content


def main() -> None:
    """Main function."""

    logging.basicConfig(level=logging.INFO)

    client = httpx.Client(headers={"Authorization": f"Bearer {ACCESS_TOKEN}"})

    zip_buffer = io.BytesIO(get_translations(client))
    with ZipFile(zip_buffer, "r") as zip_file:
        zip_file.extractall(".")


if __name__ == "__main__":
    main()
