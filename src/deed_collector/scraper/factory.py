"""Registry and factory for listing scrapers.

Scrapers register themselves with :class:`ScraperFactory` using the
:meth:`ScraperFactory.register` decorator, so adding support for a new provider
never requires editing this module (open/closed principle).
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import ClassVar

import httpx

from deed_collector.scraper.base import BaseScraper
from deed_collector.scraper.exceptions import UnsupportedProviderError


class ScraperFactory:
    """Keeps track of available scrapers and builds the right one for a URL."""

    _registry: ClassVar[list[type[BaseScraper]]] = []

    @classmethod
    def register(cls, scraper_cls: type[BaseScraper]) -> type[BaseScraper]:
        """Register ``scraper_cls`` (intended for use as a decorator)."""
        if scraper_cls not in cls._registry:
            cls._registry.append(scraper_cls)
        return scraper_cls

    @classmethod
    def get_scraper_class(cls, url: str) -> type[BaseScraper]:
        """Return the scraper class able to handle ``url``.

        Raises:
            UnsupportedProviderError: If no registered scraper matches ``url``.
        """
        for scraper_cls in cls._registry:
            if scraper_cls.can_handle(url):
                return scraper_cls

        raise UnsupportedProviderError(f"No registered scraper can handle: {url}")

    @classmethod
    def create(cls, url: str, client: httpx.Client | None = None) -> BaseScraper:
        """Instantiate the scraper responsible for ``url``."""
        scraper_cls = cls.get_scraper_class(url)
        return scraper_cls(client=client)

    @classmethod
    def supported_scrapers(cls) -> Sequence[type[BaseScraper]]:
        """Return all registered scraper classes."""
        return tuple(cls._registry)
