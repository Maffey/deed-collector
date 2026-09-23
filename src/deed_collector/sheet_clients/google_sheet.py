import unicodedata
from collections.abc import Sequence
from pathlib import Path

import gspread
from gspread.utils import ValueInputOption, rowcol_to_a1

from deed_collector.real_estate.property_listing import PropertyListing
from deed_collector.sheet_clients.base import BaseSheetClient
from deed_collector.sheet_clients.exceptions import (
    EmptyWorksheetError,
    InvalidHeaderError,
    UnknownColumnsError,
)

# TODO future work - instead of static mapping, a yaml/toml-based schema taht the user can configure.
_COLUMN_FIELDS = {
    "portal": "provider",
    "link do ogłoszenia": "url",
    "adres (do mapy)": "address",
    "cena (zł)": "price",
    "metraż (m²)": "area",
    "cena/m² (zł)": "price_per_square_meter",
    "pokoje": "number_of_rooms",
    "rynek": "market_type",
    "rok budowy": "year_of_construction",
}


class GoogleSheetClient(BaseSheetClient):
    def __init__(
        self,
        spreadsheet_id: str,
        worksheet_name: str,
        credentials_path: Path,
        header_row: int = 1,
    ):
        if header_row < 1:
            raise InvalidHeaderError(f"header_row must be >= 1, got {header_row}.")

        self.header_row = header_row
        self.client = gspread.service_account(filename=credentials_path)
        self.sheet = self.client.open_by_key(spreadsheet_id).worksheet(worksheet_name)

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
        if not any(_normalize_header(header) in _COLUMN_FIELDS for header in headers):
            raise UnknownColumnsError(
                f"No known columns found in row {self.header_row} (the header row). "
                f"Expected at least one of {sorted(_COLUMN_FIELDS)}."
            )

        row = build_sheet_row(headers, listing)
        target_row = first_empty_row_index(rows, start_row=self.header_row)
        self.sheet.update(
            [row],
            range_name=f"A{target_row}",
            value_input_option=ValueInputOption.user_entered,
        )


def _normalize_header(header: str) -> str:
    # NFC makes composed/decomposed Polish letters compare equal, and split()
    # collapses runs of whitespace (including non-breaking spaces from Sheets).
    return " ".join(unicodedata.normalize("NFC", header).split()).casefold()


def build_sheet_row(
    headers: Sequence[str], listing: PropertyListing
) -> list[str | float | int]:
    """Build a row that follows the column order defined by ``headers``.

    Cells whose header has no corresponding listing field are left blank so the
    row lines up with the sheet's actual schema.
    """
    row: list[str | float | int] = []
    for header in headers:
        field_name = _COLUMN_FIELDS.get(_normalize_header(header))
        if field_name is None:
            row.append("")
            continue
        value = getattr(listing, field_name)
        row.append("" if value is None else value)
    return row


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