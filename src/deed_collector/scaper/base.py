"""Take URL of a real estate listing, return data of said listing."""
from abc import ABC, abstractmethod
from typing import Any

import httpx

from deed_collector.real_estate.property_listing import PropertyListing


# TODO use httpx, selectolax


class BaseScraper(ABC):

    def __init__(self):
        self._client = httpx.Client(  # TODO use as conext manager
            follow_redirects=True,
            http2=True,
            transport=httpx.HTTPTransport(retries=3),
        )

    def run(self, url: str) -> PropertyListing:
        # TODO logic for retrieving raw data here
        # TODO Retreive data from the website...
        with self._client:
            response = self._client.get(url)
            response.raise_for_status()

        data = self._parse_raw(response.text)
        return self._to_property_listing(data)


    @abstractmethod
    def _parse_raw(self, raw_payload: str) -> dict[str, Any]: ...

    @abstractmethod
    def _to_property_listing(self, data: dict[str, Any]) -> PropertyListing: ...