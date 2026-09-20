from typing import Any

from deed_collector.real_estate.property_listing import PropertyListing
from deed_collector.scaper.base import BaseScraper


class OtodomScraper(BaseScraper):


    def _parse_raw(self, raw_payload: str) -> dict[str, Any]:
        print(raw_payload)

    def _to_property_listing(self, data: dict[str, Any]) -> PropertyListing: ...