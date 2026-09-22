from pathlib import Path

import typer

from deed_collector.scraper import ScraperFactory
from deed_collector.sheet_clients.common import DEFAULT_SHEET_NAME
from deed_collector.sheet_clients.google_sheet import GoogleSheetClient

_DEFAULT_CREDENTIALS_FILE_NAME = "credentials.json"
_DEFAULT_CREDENTIALS_PATH = (
    Path(__file__).resolve().parents[2] / _DEFAULT_CREDENTIALS_FILE_NAME
)


def main(
    url: str,
    spreadsheet_id: str,
    worksheet_name: str = DEFAULT_SHEET_NAME,
    credentials_path: Path = _DEFAULT_CREDENTIALS_PATH,
) -> None:
    with ScraperFactory.create(url) as scraper:
        property_listing = scraper.run(url)
    print(property_listing)

    sheet_client = GoogleSheetClient(
        spreadsheet_id=spreadsheet_id,
        worksheet_name=worksheet_name,
        credentials_path=credentials_path,
    )


if __name__ == "__main__":
    typer.run(main)
