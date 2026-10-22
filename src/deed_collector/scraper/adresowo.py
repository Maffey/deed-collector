from typing import Any

from deed_collector.real_estate.property_listing import PropertyListing
from deed_collector.scraper import BaseScraper, ScraperFactory


@ScraperFactory.register
class AdresowoScraper(BaseScraper):
    SUPPORTED_DOMAINS = ("adresowo.pl",)

    def _parse_raw(self, raw_payload: str) -> dict[str, Any]:
        pass  # TODO Implement

    def _to_property_listing(self, data: dict[str, Any], url: str) -> PropertyListing:
        pass  # TODO Implement
