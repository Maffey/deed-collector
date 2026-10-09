from dataclasses import replace

import pytest

from deed_collector.real_estate.market import MarketType
from deed_collector.real_estate.property_listing import PropertyListing
from deed_collector.real_estate.providers import Provider
from deed_collector.sheet_clients.config import (
    DEFAULT_WORKSHEET_MAPPING,
    header_to_field,
)
from deed_collector.sheet_clients.google_sheet import build_sheet_row


@pytest.fixture
def listing() -> PropertyListing:
    return PropertyListing(
        provider=Provider.OTODOM,
        url="https://example.com/1",
        address="ul. Testowa 1",
        price=500000.0,
        area=50.0,
        number_of_rooms=2,
        year_of_construction=2010,
        market_type=MarketType.SECONDARY,
    )


@pytest.fixture
def lookup() -> dict[str, str]:
    return header_to_field(DEFAULT_WORKSHEET_MAPPING)


def test_build_sheet_row_follows_header_order(listing, lookup):
    headers = ["cena (zł)", "portal", "link do ogłoszenia"]

    assert build_sheet_row(headers, listing, lookup) == [
        500000.0,
        Provider.OTODOM.value,
        "https://example.com/1",
    ]


def test_build_sheet_row_blanks_unknown_columns(listing, lookup):
    headers = ["portal", "Notatki", "cena (zł)"]

    assert build_sheet_row(headers, listing, lookup) == [
        Provider.OTODOM.value,
        "",
        500000.0,
    ]


def test_build_sheet_row_matches_headers_case_insensitively(listing, lookup):
    headers = ["  PORTAL  ", "Cena (ZŁ)"]

    assert build_sheet_row(headers, listing, lookup) == [
        Provider.OTODOM.value,
        500000.0,
    ]


def test_build_sheet_row_supports_computed_property(listing, lookup):
    assert build_sheet_row(["cena/m² (zł)"], listing, lookup) == [10000.0]


def test_build_sheet_row_blanks_missing_optional_value(listing, lookup):
    listing = replace(listing, year_of_construction=None)

    assert build_sheet_row(["rok budowy"], listing, lookup) == [""]


def test_build_sheet_row_formats_creation_date_as_iso(listing, lookup):
    headers = ["Data dodania"]

    assert build_sheet_row(headers, listing, lookup) == [
        listing.listing_creation_date.isoformat()
    ]


def test_build_sheet_row_honours_custom_mapping(listing):
    lookup = header_to_field({"price": "Moja cena"})

    assert build_sheet_row(["Moja cena"], listing, lookup) == [500000.0]


def test_build_sheet_row_skips_disabled_columns(listing):
    lookup = header_to_field({**DEFAULT_WORKSHEET_MAPPING, "price": ""})

    assert build_sheet_row(["cena (zł)"], listing, lookup) == [""]


def test_build_sheet_row_writes_comment(listing, lookup):
    listing = replace(listing, comment="Dodane przez deed-collector")

    assert build_sheet_row(["Notatki"], listing, lookup) == [
        "Dodane przez deed-collector"
    ]


def test_build_sheet_row_blanks_empty_comment(listing, lookup):
    assert build_sheet_row(["Notatki"], listing, lookup) == [""]
