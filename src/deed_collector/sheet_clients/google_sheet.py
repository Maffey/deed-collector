import gspread
from gspread.utils import ValueInputOption

from deed_collector.real_estate.property_listing import PropertyListing
from deed_collector.sheet_clients.base import BaseSheetClient


class GoogleSheetClient(BaseSheetClient):
    def __init__(self, credentials_path: str, spreadsheet_id: str, worksheet_name: str = "Sheet1"):
        self.client = gspread.service_account(filename=credentials_path)
        self.sheet = self.client.open_by_key(spreadsheet_id).worksheet(worksheet_name)

    def append_listing(self, listing: PropertyListing) -> None:
        """Append a single listing row."""
        self.sheet.append_row(
            listing.to_sheet_row(),
            value_input_option=ValueInputOption.user_entered
        )