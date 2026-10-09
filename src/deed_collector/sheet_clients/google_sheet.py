from collections.abc import Mapping, Sequence
from datetime import date
from pathlib import Path

import gspread
from gspread.utils import ValueInputOption, rowcol_to_a1

from deed_collector.real_estate.property_listing import PropertyListing
from deed_collector.sheet_clients.base import BaseSheetClient
from deed_collector.sheet_clients.config import (
    DEFAULT_WORKSHEET_MAPPING,
    header_to_field,
    normalize_header,
)
from deed_collector.sheet_clients.exceptions import (
    EmptyWorksheetError,
    InvalidHeaderError,
    UnknownColumnsError,
)


class GoogleSheetClient(BaseSheetClient):
    def __init__(
        self,
        spreadsheet_id: str,
        worksheet_name: str,
        credentials_path: Path,
        header_row: int = 1,
        column_mapping: Mapping[str, str] | None = None,
    ):
        if header_row < 1:
            raise InvalidHeaderError(f"header_row must be >= 1, got {header_row}.")

        self.header_row = header_row
        self.column_mapping = (
            dict(column_mapping)
            if column_mapping is not None
            else dict(DEFAULT_WORKSHEET_MAPPING)
        )
        self.client = gspread.service_account(filename=credentials_path)
        self.sheet = self.client.open_by_key(spreadsheet_id).worksheet(worksheet_name)

    def get_headers(self) -> list[str]:
        """Return the header row as text, or ``[]`` when the row is empty."""
        start = rowcol_to_a1(self.header_row, 1)
        end = rowcol_to_a1(self.header_row, self.sheet.col_count)
        rows = self.sheet.get(f"{start}:{end}")
        return list(rows[0]) if rows else []

    def append_listing(self, listing: PropertyListing) -> None:
        """Append a single listing row, matching the sheet's header layout."""
        # Read from the header row down so that row offsets stay absolute, even
        # though the values API trims leading empty rows and columns.
        start = rowcol_to_a1(self.header_row, 1)
        end = rowcol_to_a1(self.sheet.row_count, self.sheet.col_count)
        rows = self.sheet.get(f"{start}:{end}")
        if not rows:
            raise EmptyWorksheetError(
                f"The worksheet has no data from header row {self.header_row} down."
            )

        headers = rows[0]
        lookup = header_to_field(self.column_mapping)
        if not any(normalize_header(header) in lookup for header in headers):
            configured = sorted(
                column for column in self.column_mapping.values() if column.strip()
            )
            raise UnknownColumnsError(
                f"No known columns found in row {self.header_row} (the header row). "
                f"Expected at least one of the configured columns: {configured}."
            )

        row = build_sheet_row(headers, listing, lookup)
        target_row = first_empty_row_index(rows, start_row=self.header_row)
        self.sheet.update(
            [row],
            range_name=f"A{target_row}",
            value_input_option=ValueInputOption.user_entered,
        )


def build_sheet_row(
    headers: Sequence[str],
    listing: PropertyListing,
    lookup: dict[str, str],
) -> list[str | float | int]:
    row: list[str | float | int] = []
    for header in headers:
        field_name = lookup.get(normalize_header(header))
        if field_name is None:
            row.append("")
            continue
        value = getattr(listing, field_name)
        row.append(serialize_cell(value))
    return row


def serialize_cell(value: object) -> str | float | int:
    """Convert a listing field into a value the Sheets API accepts.

    ``None`` becomes an empty cell, and ``date``/``datetime`` values are written
    in ISO 8601 (``YYYY-MM-DD``) so the API can serialize them.
    """
    if value is None:
        return ""
    # ``datetime`` is a subclass of ``date``, so this covers both.
    if isinstance(value, date):
        return value.isoformat()
    return value


def first_empty_row_index(rows: Sequence[Sequence[str]], start_row: int = 1) -> int:
    """Return the 1-based index of the first row without any values.

    ``rows`` is read starting at the absolute ``start_row`` (so ``rows[0]`` maps
    to ``start_row``). The Sheets values API ignores rows that carry formatting
    but no data, so relying on it lets us target the first data-free row instead
    of the row below stale formatting (which is where ``append_row`` would put
    us).
    """
    for offset, row in enumerate(rows):
        if not any(cell != "" for cell in row):
            return start_row + offset
    return start_row + len(rows)
