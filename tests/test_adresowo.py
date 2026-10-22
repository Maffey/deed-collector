import json

import httpx
import pytest

from deed_collector.real_estate.market import MarketType
from deed_collector.real_estate.property_listing import PropertyListing
from deed_collector.real_estate.providers import Provider
from deed_collector.scraper.exceptions import ParsingError
from deed_collector.scraper.factory import ScraperFactory

URL = "https://adresowo.pl/o/dom-przykladowo-przykladow-ul-zmyslona-t0e5s7"

DEFAULT_ADDRESS = (
    "ul. Zmyślona, Przykładów, gmina Przykładowa, powiat Testowy, województwo Fikcyjne"
)
DEFAULT_PLACE_NAME = (
    "Przykładów, ul. Zmyślona Dom szeregowy do zamieszkania - 141 m² - 4 pokoje"
)


def _script(payload: dict) -> str:
    return (
        '<script type="application/ld+json">'
        f"{json.dumps(payload, ensure_ascii=False)}"
        "</script>"
    )


def build_adresowo_html(
    *,
    offer_price: str | None = "1249000",
    area: str | None = "140,6 m²",
    rooms: str | None = "4 pokoje",
    year: str | None = "2006",
    place_name: str = DEFAULT_PLACE_NAME,
    place_address: str = DEFAULT_ADDRESS,
    market: str | None = "SecondaryMarket",
    include_offer: bool = True,
    include_place: bool = True,
) -> str:
    """Build a minimal Adresowo listing page."""
    header_parts = [
        '<span class="block">1&nbsp;249&nbsp;000 <span>zł</span></span>',
        '<span class="block">8&nbsp;883 zł / m²</span>',
    ]
    if area is not None:
        header_parts.append(f'<span class="block">{area}</span>')
    if rooms is not None:
        header_parts.append(f'<span class="block">{rooms}</span>')
    if year is not None:
        header_parts.extend(
            [
                f'<span class="block">{year}</span>',
                '<span class="block">rok budowy</span>',
            ]
        )

    scripts = []
    if include_offer:
        offer = {
            "@context": "https://schema.org",
            "@type": "Offer",
            "priceCurrency": "PLN",
            "url": URL,
        }
        if offer_price is not None:
            offer["price"] = offer_price
        scripts.append(_script({"@context": "https://schema.org", "@graph": [offer]}))

    if include_place:
        place = {
            "@context": "https://schema.org",
            "@type": "Place",
            "address": {"@type": "PostalAddress", "streetAddress": place_address},
            "name": place_name,
        }
        scripts.append(_script({"@context": "https://schema.org", "@graph": [place]}))

    market_link = (
        f'<a href="https://example.com/?loanPurpose.market={market}">kredyt</a>'
        if market is not None
        else ""
    )

    return (
        "<html><body>"
        '<header id="offer-navigation">'
        + "".join(header_parts)
        + market_link
        + "</header>"
        + "".join(scripts)
        + "</body></html>"
    )


def _scraper_for(html: str):
    client = httpx.Client(
        transport=httpx.MockTransport(lambda _: httpx.Response(200, text=html))
    )
    return client, ScraperFactory.create(URL, client=client)


def test_factory_routes_adresowo_url():
    assert ScraperFactory.get_scraper_class(URL).__name__ == "AdresowoScraper"


def test_run_maps_listing_fields():
    client, scraper = _scraper_for(build_adresowo_html())

    listing = scraper.run(URL)

    assert isinstance(listing, PropertyListing)
    assert listing.provider is Provider.ADRESOWO
    assert listing.url == URL
    assert listing.address == DEFAULT_ADDRESS
    assert listing.price == 1249000.0
    assert listing.area == 140.6
    assert listing.number_of_rooms == 4
    assert listing.year_of_construction == 2006
    assert listing.market_type is MarketType.SECONDARY
    assert listing.price_per_square_meter == pytest.approx(1249000.0 / 140.6)
    client.close()


def test_rooms_fall_back_to_place_name():
    client, scraper = _scraper_for(build_adresowo_html(rooms=None))

    assert scraper.run(URL).number_of_rooms == 4
    client.close()


def test_area_falls_back_to_place_name():
    client, scraper = _scraper_for(build_adresowo_html(area=None))

    assert scraper.run(URL).area == 141.0
    client.close()


def test_address_falls_back_to_map_markup():
    html = build_adresowo_html(include_place=False).replace(
        "</header>",
        '</header><span itemprop="addressLocality">Przykładów</span>'
        '<span itemprop="streetAddress">Zmyślona</span>',
    )
    client, scraper = _scraper_for(html)

    assert scraper.run(URL).address == "Zmyślona, Przykładów"
    client.close()


def test_primary_market_from_market_url():
    client, scraper = _scraper_for(build_adresowo_html(market="PrimaryMarket"))

    assert scraper.run(URL).market_type is MarketType.PRIMARY
    client.close()


def test_missing_market_defaults_to_secondary():
    client, scraper = _scraper_for(build_adresowo_html(market=None))

    assert scraper.run(URL).market_type is MarketType.SECONDARY
    client.close()


def test_missing_year_maps_to_none():
    client, scraper = _scraper_for(build_adresowo_html(year=None))

    assert scraper.run(URL).year_of_construction is None
    client.close()


def test_missing_offer_raises_parsing_error():
    client, scraper = _scraper_for(build_adresowo_html(include_offer=False))

    with pytest.raises(ParsingError, match="'Offer'"):
        scraper.run(URL)
    client.close()


def test_missing_price_raises_parsing_error():
    client, scraper = _scraper_for(build_adresowo_html(offer_price=None))

    with pytest.raises(ParsingError, match="price"):
        scraper.run(URL)
    client.close()


def test_invalid_json_ld_does_not_break_parsing():
    html = "<html><body>" + build_adresowo_html().replace(
        '<script type="application/ld+json">',
        '<script type="application/ld+json">not-json</script>'
        '<script type="application/ld+json">',
        1,
    )
    client, scraper = _scraper_for(html)

    assert scraper.run(URL).price == 1249000.0
    client.close()


def test_mapping_failure_is_wrapped_in_parsing_error():
    client, scraper = _scraper_for(build_adresowo_html(offer_price="not-a-number"))

    with pytest.raises(ParsingError):
        scraper.run(URL)
    client.close()
