from typing import Any
from datetime import datetime
import json
from typing import Any

from selectolax.parser import HTMLParser

from deed_collector.real_estate.property_listing import (
    MarketType,
    PropertyListing,
    Provider,
)
from deed_collector.scaper.base import BaseScraper


class OtodomScraper(BaseScraper):
    def _parse_raw(self, raw_payload: str) -> dict[str, Any]:
        """Extracts the 'ad' data dictionary from Next.js hydration script."""
        tree = HTMLParser(raw_payload)
        next_data_node = tree.css_first("script#__NEXT_DATA__")

        if not next_data_node:
            raise ValueError("Could not find '__NEXT_DATA__' script tag in HTML.")

        payload = json.loads(next_data_node.text())
        page_props = payload.get("props", {}).get("pageProps", {})

        ad_data = page_props.get("ad")
        if not ad_data:
            raise ValueError("Listing data ('ad') not found in '__NEXT_DATA__'.")

        return ad_data

    def _to_property_listing(self, data: dict[str, Any]) -> PropertyListing:
        """Maps raw ad dictionary to the PropertyListing model."""
        target: dict[str, Any] = data.get("target", {})
        attributes: dict[str, Any] = data.get("attributes", {})

        # address (combining street if available with reverse geocoded locality)
        location_data = data.get("location", {})
        street_name = (
            location_data.get("address", {}).get("street", {}).get("name")
        )

        locations = (
            location_data.get("reverseGeocoding", {}).get("locations", [])
        )
        locality_desc = locations[-1].get("fullName") if locations else ""

        if street_name and locality_desc:
            address = f"{street_name}, {locality_desc}"
        else:
            address = street_name or locality_desc or ""

        # price
        price = float(target.get("Price", 0))

        # area (m²)
        raw_area = target.get("Area") or attributes.get("m")
        area = float(raw_area) if raw_area is not None else 0.0

        # number_of_rooms
        raw_rooms = target.get("Rooms_num") or attributes.get("rooms_num")
        if isinstance(raw_rooms, list):
            number_of_rooms = int(raw_rooms[0])
        elif raw_rooms is not None:
            number_of_rooms = int(raw_rooms)
        else:
            number_of_rooms = 0

        # year_of_construction
        raw_year = target.get("Build_year") or attributes.get("build_year")
        year_of_construction = int(raw_year) if raw_year else None

        # market_type
        raw_market = (
            target.get("MarketType") or attributes.get("market") or ""
        ).lower()
        if "primary" in raw_market or "pierwotny" in raw_market:
            market_type = MarketType.PRIMARY
        else:
            market_type = MarketType.SECONDARY

        return PropertyListing(
            provider=Provider.OTODOM,
            url=self._url,
            address=address,
            price=price,
            area=area,
            number_of_rooms=number_of_rooms,
            year_of_construction=year_of_construction,
            market_type=market_type,
        )