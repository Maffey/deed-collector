"""Exceptions raised by the scraper layer.

All scraper-specific errors derive from :class:`ScraperError`, so callers can
catch the whole family with a single ``except`` clause while still being able to
handle individual failure modes if they need to.
"""


class ScraperError(Exception):
    """Base exception for all scraper-related errors."""


class UnsupportedProviderError(ScraperError):
    """Raised when no registered scraper can handle the given URL."""


class ParsingError(ScraperError):
    """Raised when the fetched payload is malformed or its structure changed."""
