import pytest

from deed_collector.scraper.factory import ScraperFactory


@pytest.fixture
def registry():
    """Run a test against a private registry and restore it afterwards."""
    original = list(ScraperFactory._registry)
    ScraperFactory._registry.clear()
    yield ScraperFactory._registry
    ScraperFactory._registry[:] = original
