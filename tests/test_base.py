import httpx
import pytest

from deed_collector.scraper.base import BaseScraper
from deed_collector.scraper.exceptions import ParsingError


class EchoScraper(BaseScraper):
    SUPPORTED_DOMAINS = ("example.com",)

    def _parse_raw(self, raw_payload: str) -> dict:
        return {"raw": raw_payload}

    def _to_property_listing(self, data: dict, url: str):
        return data["raw"], url


class BrokenScraper(EchoScraper):
    def _parse_raw(self, raw_payload: str) -> dict:
        raise KeyError("ad")


def _client(response_factory):
    return httpx.Client(transport=httpx.MockTransport(response_factory))


def test_run_keeps_injected_client_open_across_calls():
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.url)
        return httpx.Response(200, text="<html></html>")

    client = _client(handler)
    scraper = EchoScraper(client=client)

    assert scraper.run("https://example.com/1") == (
        "<html></html>",
        "https://example.com/1",
    )
    assert scraper.run("https://example.com/2") == (
        "<html></html>",
        "https://example.com/2",
    )

    assert len(calls) == 2
    assert not client.is_closed
    client.close()


def test_close_leaves_injected_client_open():
    client = _client(lambda _: httpx.Response(200, text=""))
    scraper = EchoScraper(client=client)

    scraper.close()

    assert not client.is_closed
    client.close()


def test_close_closes_owned_client():
    scraper = EchoScraper()

    scraper.close()

    assert scraper._client.is_closed


def test_context_manager_closes_owned_client():
    with EchoScraper() as scraper:
        client = scraper._client

    assert client.is_closed


def test_run_raises_parsing_error_for_bad_payload():
    client = _client(lambda _: httpx.Response(200, text="<html></html>"))
    scraper = BrokenScraper(client=client)

    with pytest.raises(ParsingError) as excinfo:
        scraper.run("https://example.com/1")

    assert isinstance(excinfo.value.__cause__, KeyError)
    client.close()
