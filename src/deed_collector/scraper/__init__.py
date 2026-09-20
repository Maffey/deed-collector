"""Scraper layer: provider-specific listing scrapers and their factory."""

from deed_collector.scraper.base import BaseScraper
from deed_collector.scraper.exceptions import (
    ParsingError,
    ScraperError,
    UnsupportedProviderError,
)
from deed_collector.scraper.factory import ScraperFactory

# Importing concrete scrapers triggers their self-registration with the
# factory. Keep these imports after the factory to avoid circular imports.
from deed_collector.scraper.otodom import OtodomScraper

__all__ = [
    "BaseScraper",
    "OtodomScraper",
    "ParsingError",
    "ScraperError",
    "ScraperFactory",
    "UnsupportedProviderError",
]
