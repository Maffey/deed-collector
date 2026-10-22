"""Scraper layer: provider-specific listing scrapers and their factory."""

# Importing a concrete scraper registers it with the factory, so import them
# here to populate the registry whenever the package is imported.
from deed_collector.scraper.adresowo import AdresowoScraper
from deed_collector.scraper.base import BaseScraper
from deed_collector.scraper.exceptions import (
    ParsingError,
    ScraperError,
    UnsupportedProviderError,
)
from deed_collector.scraper.factory import ScraperFactory
from deed_collector.scraper.otodom import OtodomScraper

__all__ = [
    "AdresowoScraper",
    "BaseScraper",
    "OtodomScraper",
    "ParsingError",
    "ScraperError",
    "ScraperFactory",
    "UnsupportedProviderError",
]
