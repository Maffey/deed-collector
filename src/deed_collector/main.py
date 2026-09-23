from pathlib import Path
from typing import Annotated

import typer
from loguru import logger

from deed_collector.real_estate.market import MarketType
from deed_collector.real_estate.property_listing import PropertyListing
from deed_collector.real_estate.providers import Provider
from deed_collector.sheet_clients.common import DEFAULT_SHEET_NAME
from deed_collector.sheet_clients.google_sheet import GoogleSheetClient

_DEFAULT_CREDENTIALS_FILE_NAME = "credentials.json"
_DEFAULT_CREDENTIALS_PATH = (
    Path(__file__).resolve().parents[2] / _DEFAULT_CREDENTIALS_FILE_NAME
)


def main(
    url: Annotated[
        str,
        typer.Argument(help="URL of the property listing to scrape."),
    ],
    spreadsheet_id: Annotated[
        str,
        typer.Argument(
            help="The ID of the Google Spreadsheet (found in the sheet URL: /spreadsheets/d/<ID>/edit)."
        ),
    ],
    sheet_name: Annotated[
        str,
        typer.Option(
            "--sheet-name",
            "-w",
            help="The name of the sheet tab within the spreadsheet.",
        ),
    ] = DEFAULT_SHEET_NAME,
    credentials_path: Annotated[
        Path,
        typer.Option(
            "--credentials-path",
            "-c",
            help="Path to the Google Service Account credentials JSON file.",
            exists=True,
            file_okay=True,
            dir_okay=False,
            readable=True,
        ),
    ] = _DEFAULT_CREDENTIALS_PATH,
    header_row: Annotated[
        int,
        typer.Option(
            "--header-row",
            "-r",
            help="1-based row number that holds the sheet's column headers.",
            min=1,
        ),
    ] = 1,
) -> None:

    # TODO restore later
    # with ScraperFactory.create(url) as scraper:
    #     property_listing = scraper.run(url)

    property_listing = PropertyListing(
        provider=Provider.OTODOM,
        url="https://www.example.com/some-url",
        address="ul. Nieistniejaca 27/3, Zbignieszów",
        price=1100000.0,
        area=101.0,
        number_of_rooms=5,
        year_of_construction=2025,
        market_type=MarketType.PRIMARY,
    )
    logger.debug(property_listing)

    sheet_client = GoogleSheetClient(
        spreadsheet_id=spreadsheet_id,
        worksheet_name=sheet_name,
        credentials_path=credentials_path,
        header_row=header_row,
    )

    sheet_client.append_listing(property_listing)


if __name__ == "__main__":
    typer.run(main)
