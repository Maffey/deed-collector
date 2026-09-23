"""Exceptions raised by the sheet client layer.

All sheet-client-specific errors derive from :class:`SheetClientError`, which in
turn derives from the package root :class:`DeedCollectorError`, so callers can
catch the whole family with a single ``except`` clause.
"""

from deed_collector.exceptions import DeedCollectorError


class SheetClientError(DeedCollectorError):
    """Base exception for all sheet client errors."""


class InvalidHeaderError(SheetClientError):
    """Raised when the configured header row is not a valid 1-based row."""


class EmptyWorksheetError(SheetClientError):
    """Raised when the worksheet has no data from the header row down."""


class UnknownColumnsError(SheetClientError):
    """Raised when the header row contains none of the known columns."""
