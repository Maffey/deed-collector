"""Scraper for adresowo.pl listings."""

from __future__ import annotations

import json
import re
from typing import Any

from selectolax.lexbor import LexborHTMLParser

from deed_collector.real_estate.property_listing import (
    MarketType,
    PropertyListing,
    Provider,
)
from deed_collector.scraper.base import BaseScraper
from deed_collector.scraper.exceptions import ParsingError
from deed_collector.scraper.factory import ScraperFactory

# Values in the listing header look like "140,6 m²" and "4 pokoje".
_AREA_PATTERN = re.compile(r"^[\d\s.,]+m²$")
_ROOMS_PATTERN = re.compile(r"^(\d+)\s*pok(?:oje|oi|ój)$", re.IGNORECASE)
_ROOMS_IN_TEXT_PATTERN = re.compile(r"(\d+)\s*pok(?:oje|oi|ój)", re.IGNORECASE)
_YEAR_PATTERN = re.compile(r"(\d{4})\s*rok budowy")
_BUILT_YEAR_PATTERN = re.compile(r"wybudowany w (\d{4})")
_MARKET_PATTERN = re.compile(
    r"loanPurpose\.market=(PrimaryMarket|SecondaryMarket)", re.IGNORECASE
)


def _normalize_text(value: str) -> str:
    return value.replace("\xa0", " ").strip()


def _first_number(value: Any) -> float | None:
    """Return the first number from a value like ``"140,60 m²"``."""
    if value is None:
        return None

    text = _normalize_text(str(value)).replace(" ", "")
    match = re.search(r"\d+(?:[.,]\d+)?", text)
    if match is None:
        return None

    return float(match.group().replace(",", "."))


def _flatten_json_ld(payload: Any):
    """Yield every object in a JSON-LD payload, including ``@graph`` entries."""
    if isinstance(payload, list):
        for item in payload:
            yield from _flatten_json_ld(item)
    elif isinstance(payload, dict):
        yield payload
        graph = payload.get("@graph")
        if isinstance(graph, list):
            for item in graph:
                yield from _flatten_json_ld(item)


def _has_type(node: dict[str, Any], expected: str) -> bool:
    node_type = node.get("@type")
    if isinstance(node_type, list):
        return expected in node_type
    return node_type == expected


@ScraperFactory.register
class AdresowoScraper(BaseScraper):
    """Parses Adresowo listings from their JSON-LD and header markup."""

    SUPPORTED_DOMAINS = ("adresowo.pl",)

    def _parse_raw(self, raw_payload: str) -> dict[str, Any]:
        """Collect the listing data scattered across JSON-LD and the page."""
        tree = LexborHTMLParser(raw_payload)

        nodes = list(self._json_ld_nodes(tree))
        offer = next((node for node in nodes if _has_type(node, "Offer")), None)
        place = next((node for node in nodes if _has_type(node, "Place")), None)

        if offer is None:
            raise ParsingError("Could not find listing data ('Offer') in JSON-LD.")

        header = tree.css_first("header#offer-navigation")
        header_texts = (
            [_normalize_text(node.text()) for node in header.css("span.block")]
            if header is not None
            else []
        )
        header_text = _normalize_text(header.text()) if header is not None else ""

        address = self._extract_address(place, tree)
        area = self._extract_area(header_texts, place)
        rooms = self._extract_rooms(header_texts, place)
        year = self._extract_year(header_text, tree)
        market = self._extract_market(raw_payload)

        return {
            "price": offer.get("price"),
            "address": address,
            "area": area,
            "rooms": rooms,
            "year": year,
            "market": market,
        }

    def _to_property_listing(self, data: dict[str, Any], url: str) -> PropertyListing:
        """Map the collected raw values onto the :class:`PropertyListing` model."""
        raw_price = data.get("price")
        if raw_price is None:
            raise ParsingError("Listing data did not contain a price.")

        price = float(
            _normalize_text(str(raw_price)).replace(" ", "").replace(",", ".")
        )

        area = _first_number(data.get("area")) or 0.0
        rooms = _first_number(data.get("rooms"))
        number_of_rooms = int(rooms) if rooms is not None else 0

        year = _first_number(data.get("year"))
        year_of_construction = int(year) if year is not None else None

        raw_market = str(data.get("market") or "").lower()
        if "primary" in raw_market or "pierwotny" in raw_market:
            market_type = MarketType.PRIMARY
        else:
            market_type = MarketType.SECONDARY

        return PropertyListing(
            provider=Provider.ADRESOWO,
            url=url,
            address=str(data.get("address") or ""),
            price=price,
            area=area,
            number_of_rooms=number_of_rooms,
            year_of_construction=year_of_construction,
            market_type=market_type,
        )

    @staticmethod
    def _json_ld_nodes(tree: LexborHTMLParser):
        """Yield all JSON-LD objects; ignore scripts that are not valid JSON."""
        for node in tree.css('script[type="application/ld+json"]'):
            try:
                payload = json.loads(node.text())
            except json.JSONDecodeError, TypeError:
                continue

            yield from _flatten_json_ld(payload)

    @staticmethod
    def _extract_address(place: dict[str, Any] | None, tree: LexborHTMLParser) -> str:
        if place is not None:
            address_data = place.get("address", {})
            if isinstance(address_data, dict):
                street_address = address_data.get("streetAddress")
                if street_address:
                    return _normalize_text(str(street_address))

        # Fallback to the address shown on the map card.
        locality_node = tree.css_first('[itemprop="addressLocality"]')
        street_node = tree.css_first('[itemprop="streetAddress"]')
        locality = _normalize_text(locality_node.text()) if locality_node else ""
        street = _normalize_text(street_node.text()) if street_node else ""

        if street and locality:
            return f"{street}, {locality}"
        return street or locality

    @staticmethod
    def _extract_area(
        header_texts: list[str], place: dict[str, Any] | None
    ) -> str | None:
        for text in header_texts:
            if _AREA_PATTERN.match(text):
                return text

        if place is not None:
            match = re.search(r"[\d\s.,]+\s*m²", str(place.get("name") or ""))
            if match is not None:
                return _normalize_text(match.group())

        return None

    @staticmethod
    def _extract_rooms(
        header_texts: list[str], place: dict[str, Any] | None
    ) -> str | None:
        for text in header_texts:
            if _ROOMS_PATTERN.match(text):
                return text

        if place is not None:
            match = _ROOMS_IN_TEXT_PATTERN.search(str(place.get("name") or ""))
            if match is not None:
                return match.group()

        return None

    @staticmethod
    def _extract_year(header_text: str, tree: LexborHTMLParser) -> str | None:
        match = _YEAR_PATTERN.search(header_text)
        if match is not None:
            return match.group(1)

        body_text = _normalize_text(tree.body.text()) if tree.body else ""
        match = _YEAR_PATTERN.search(body_text) or _BUILT_YEAR_PATTERN.search(body_text)
        return match.group(1) if match is not None else None

    @staticmethod
    def _extract_market(raw_payload: str) -> str | None:
        match = _MARKET_PATTERN.search(raw_payload)
        return match.group(1) if match is not None else None
