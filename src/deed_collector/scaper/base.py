"""Take URL of a real estate listing, return data of said listing."""
from abc import ABC, abstractmethod
from typing import Any

import httpx

from deed_collector.real_estate.property_listing import PropertyListing


# TODO use httpx, selectolax


class BaseScraper(ABC):

    def __init__(self, url: str):
        self._url = url
        self._client = httpx.Client(  # TODO use as conext manager
            follow_redirects=True,
            http2=True,
            transport=httpx.HTTPTransport(retries=3),
            headers={
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "pl-PL,pl;q=0.9,en-US;q=0.8,en;q=0.7",
}
        )

    def run(self) -> PropertyListing:
        # TODO logic for retrieving raw data here
        # TODO Retreive data from the website...
        with self._client:
            response = self._client.get(self._url)
            response.raise_for_status()

        data = self._parse_raw(response.text)
        return self._to_property_listing(data)


    @abstractmethod
    def _parse_raw(self, raw_payload: str) -> dict[str, Any]: ...

    @abstractmethod
    def _to_property_listing(self, data: dict[str, Any]) -> PropertyListing: ...