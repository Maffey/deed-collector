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


class SheetConfigError(SheetClientError):
    """Base exception for worksheet configuration problems."""


class ColumnMappingError(SheetConfigError):
    """Base exception for worksheet column mapping configuration problems."""


class ConfigFileError(SheetConfigError):
    """Raised when the config file cannot be read or parsed."""


class UnknownMappingFieldError(ColumnMappingError):
    """Raised when the config maps a field that PropertyListing does not expose."""


class InvalidColumnMappingError(ColumnMappingError):
    """Raised when a mapping value is invalid or a column is mapped twice."""


class InvalidSheetSettingsError(SheetConfigError):
    """Raised when the ``[worksheet]`` settings table is invalid."""


class SetupCancelledError(SheetClientError):
    """Raised when the interactive mapping setup is aborted by the user."""
