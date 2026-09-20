"""Take the URL of a real-estate listing and return the parsed listing."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Self
from urllib.parse import urlparse

import httpx

from deed_collector.real_estate.property_listing import PropertyListing
from deed_collector.scraper.exceptions import ParsingError

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,"
        "image/avif,image/webp,*/*;q=0.8"
    ),
    "Accept-Language": "pl-PL,pl;q=0.9,en-US;q=0.8,en;q=0.7",
}

DEFAULT_TIMEOUT = 15.0


class BaseScraper(ABC):
    """Base class for all real-estate listing scrapers.

    Subclasses declare the domains they support via :attr:`SUPPORTED_DOMAINS`
    and are responsible for turning a raw payload into a ``PropertyListing``.
    """

    #: Domains (including subdomains) this scraper knows how to handle.
    SUPPORTED_DOMAINS: tuple[str, ...] = ()

    def __init__(self, client: httpx.Client | None = None) -> None:
        # An injected client is owned by the caller; one we create is ours to
        # close. This distinction keeps ``close()`` safe either way.
        self._owns_client = client is None
        self._client = client or httpx.Client(
            follow_redirects=True,
            headers=DEFAULT_HEADERS,
            timeout=DEFAULT_TIMEOUT,
            transport=httpx.HTTPTransport(retries=3, http2=True),
        )

    @classmethod
    def can_handle(cls, url: str) -> bool:
        """Return ``True`` if this scraper knows how to handle ``url``."""
        host = (urlparse(url).hostname or "").lower()
        return any(
            host == domain or host.endswith(f".{domain}")
            for domain in cls.SUPPORTED_DOMAINS
        )

    def run(self, url: str) -> PropertyListing:
        """Fetch ``url`` and return the parsed :class:`PropertyListing`."""
        response = self._client.get(url)
        response.raise_for_status()

        try:
            data = self._parse_raw(response.text)
            return self._to_property_listing(data, url)
        except ParsingError:
            raise
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise ParsingError(f"Could not parse listing at {url!r}") from exc

    def close(self) -> None:
        """Close the HTTP client if this instance owns it."""
        if self._owns_client:
            self._client.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    @abstractmethod
    def _parse_raw(self, raw_payload: str) -> dict[str, Any]:
        """Extract the provider-specific data structure from a raw payload."""

    @abstractmethod
    def _to_property_listing(self, data: dict[str, Any], url: str) -> PropertyListing:
        """Map the provider-specific data structure onto our model."""
