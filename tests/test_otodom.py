import json

import httpx
import pytest

from deed_collector.real_estate.market import MarketType
from deed_collector.real_estate.property_listing import PropertyListing
from deed_collector.real_estate.providers import Provider
from deed_collector.scraper.exceptions import ParsingError
from deed_collector.scraper.factory import ScraperFactory

URL = "https://www.otodom.pl/pl/oferta/test-ID123"

AD = {
    "target": {
        "Price": "750000",
        "Area": "50",
        "Rooms_num": ["3"],
        "Build_year": "2015",
        "MarketType": "secondary",
    },
    "attributes": {},
    "location": {
        "address": {"street": {"name": "Testowa"}},
        "reverseGeocoding": {"locations": [{"fullName": "Warszawa, Mokotów"}]},
    },
}


def build_otodom_html(ad: dict) -> str:
    """Wrap an Otodom ``ad`` payload in a minimal ``__NEXT_DATA__`` document."""
    payload = {"props": {"pageProps": {"ad": ad}}}
    return (
        "<html><body>"
        '<script id="__NEXT_DATA__" type="application/json">'
        f"{json.dumps(payload)}"
        "</script>"
        "</body></html>"
    )


def _scraper_for(html: str):
    client = httpx.Client(
        transport=httpx.MockTransport(lambda _: httpx.Response(200, text=html))
    )
    return client, ScraperFactory.create(URL, client=client)


def test_factory_routes_otodom_url():
    assert ScraperFactory.get_scraper_class(URL).__name__ == "OtodomScraper"


def test_run_maps_listing_fields():
    client, scraper = _scraper_for(build_otodom_html(AD))

    listing = scraper.run(URL)

    assert isinstance(listing, PropertyListing)
    assert listing.provider is Provider.OTODOM
    assert listing.url == URL
    assert listing.address == "Testowa, Warszawa, Mokotów"
    assert listing.price == 750000.0
    assert listing.area == 50.0
    assert listing.number_of_rooms == 3
    assert listing.year_of_construction == 2015
    assert listing.market_type is MarketType.SECONDARY
    assert listing.price_per_square_meter == 15000.0
    client.close()


def test_primary_market_from_polish_value():
    ad = {**AD, "target": {**AD["target"], "MarketType": "pierwotny"}}
    client, scraper = _scraper_for(build_otodom_html(ad))

    assert scraper.run(URL).market_type is MarketType.PRIMARY
    client.close()


def test_missing_next_data_raises_parsing_error():
    client, scraper = _scraper_for("<html><body>no payload</body></html>")

    with pytest.raises(ParsingError, match="__NEXT_DATA__"):
        scraper.run(URL)
    client.close()


def test_missing_ad_raises_parsing_error():
    client, scraper = _scraper_for(build_otodom_html({}))

    with pytest.raises(ParsingError, match="'ad'"):
        scraper.run(URL)
    client.close()


def test_invalid_json_raises_parsing_error():
    html = '<html><body><script id="__NEXT_DATA__">not-json</script></body></html>'
    client, scraper = _scraper_for(html)

    with pytest.raises(ParsingError, match="valid JSON"):
        scraper.run(URL)
    client.close()


def test_mapping_failure_is_wrapped_in_parsing_error():
    ad = {**AD, "target": {**AD["target"], "Price": "not-a-number"}}
    client, scraper = _scraper_for(build_otodom_html(ad))

    with pytest.raises(ParsingError):
        scraper.run(URL)
    client.close()
