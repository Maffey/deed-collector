import httpx
import pytest

from deed_collector.scraper.base import BaseScraper
from deed_collector.scraper.exceptions import UnsupportedProviderError
from deed_collector.scraper.factory import ScraperFactory


class ExampleScraper(BaseScraper):
    SUPPORTED_DOMAINS = ("example.com",)

    def _parse_raw(self, raw_payload: str) -> dict:
        return {"raw": raw_payload}

    def _to_property_listing(self, data: dict, url: str):
        return (data, url)


class OtherScraper(BaseScraper):
    SUPPORTED_DOMAINS = ("other.pl",)

    def _parse_raw(self, raw_payload: str) -> dict:
        return {}

    def _to_property_listing(self, data: dict, url: str):
        return None


def test_register_is_idempotent(registry):
    ScraperFactory.register(ExampleScraper)
    ScraperFactory.register(ExampleScraper)

    assert registry == [ExampleScraper]


@pytest.mark.parametrize(
    "url",
    [
        "https://example.com/listing/1",
        "https://www.example.com/listing/1",
        "http://deep.sub.example.com/path",
    ],
)
def test_can_handle_matches_domain_and_subdomains(url):
    assert ExampleScraper.can_handle(url)


@pytest.mark.parametrize(
    "url",
    [
        "https://notexample.com/listing/1",
        "https://example.com.evil.com/listing/1",
        "https://other.pl/listing/1",
    ],
)
def test_can_handle_rejects_unrelated_hosts(url):
    assert not ExampleScraper.can_handle(url)


def test_get_scraper_class_picks_first_match(registry):
    ScraperFactory.register(ExampleScraper)
    ScraperFactory.register(OtherScraper)

    assert ScraperFactory.get_scraper_class("https://other.pl/x") is OtherScraper


def test_get_scraper_class_raises_for_unknown_provider(registry):
    ScraperFactory.register(ExampleScraper)

    with pytest.raises(UnsupportedProviderError, match="unknown.test"):
        ScraperFactory.get_scraper_class("https://unknown.test/x")


def test_create_injects_client(registry):
    ScraperFactory.register(ExampleScraper)
    client = httpx.Client(transport=httpx.MockTransport(lambda _: httpx.Response(200)))

    scraper = ScraperFactory.create("https://example.com/x", client=client)

    assert isinstance(scraper, ExampleScraper)
    client.close()


def test_registered_scrapers_include_otodom():
    from deed_collector.scraper import OtodomScraper

    assert OtodomScraper in ScraperFactory.supported_scrapers()
