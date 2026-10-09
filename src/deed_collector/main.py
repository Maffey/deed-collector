import sys
from pathlib import Path
import random
from typing import Annotated

import typer
from loguru import logger

from deed_collector.real_estate.market import MarketType
from deed_collector.real_estate.property_listing import PropertyListing
from deed_collector.real_estate.providers import Provider
from deed_collector.sheet_clients.config import (
    DEFAULT_CONFIG_FILE_NAME,
    SETTINGS_SECTION,
    load_sheet_settings,
    load_worksheet_mapping,
)
from deed_collector.sheet_clients.exceptions import (
    ColumnMappingError,
    SetupCancelledError,
    SheetConfigError,
)
from deed_collector.sheet_clients.google_sheet import GoogleSheetClient
from deed_collector.sheet_clients.setup import run_setup_wizard

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
        str | None,
        typer.Argument(
            help=(
                "The ID of the Google Spreadsheet (found in the sheet URL: "
                "/spreadsheets/d/<ID>/edit). May also be set in the config file."
            )
        ),
    ] = None,
    sheet_name: Annotated[
        str | None,
        typer.Option(
            "--sheet-name",
            "-w",
            help="The name of the sheet tab within the spreadsheet. Overrides config.",
        ),
    ] = None,
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
        int | None,
        typer.Option(
            "--header-row",
            "-r",
            help=(
                "1-based row number that holds the sheet's column headers. "
                "Overrides config."
            ),
            min=1,
        ),
    ] = None,
    config_path: Annotated[
        Path,
        typer.Option(
            "--config-path",
            "-f",
            help="TOML file mapping listing fields to your worksheet columns.",
            dir_okay=False,
        ),
    ] = Path(DEFAULT_CONFIG_FILE_NAME),
    setup: Annotated[
        bool,
        typer.Option(
            "--setup",
            help="Force the interactive worksheet mapping setup, then continue.",
        ),
    ] = False,
) -> None:

    # TODO restore later
    # with ScraperFactory.create(url) as scraper:
    #     property_listing = scraper.run(url)
    price_base = 1_100_000.0
    price_diff = 100_00
    area_base = 100
    area_diff = 5
    property_listing = PropertyListing(
        provider=Provider.OTODOM,
        url="https://www.example.com/some-url",
        address="ul. Nieistniejaca 27/3, Zbignieszów",
        price=random.uniform(price_base-price_diff, price_base+price_diff),
        area=random.randint(area_base-area_diff, area_base+area_diff),
        number_of_rooms=5,
        year_of_construction=2025,
        market_type=MarketType.PRIMARY,
    )
    logger.debug(property_listing)

    # CLI values win, then the config file, then the built-in defaults.
    try:
        settings = load_sheet_settings(config_path)
    except SheetConfigError as exc:
        logger.error(str(exc))
        raise typer.Exit(code=1) from exc

    settings = settings.overridden_by(
        spreadsheet_id=spreadsheet_id,
        sheet_name=sheet_name,
        header_row=header_row,
    )
    if settings.spreadsheet_id is None:
        logger.error(
            "No spreadsheet id provided. Pass it as an argument or set "
            f"'spreadsheet_id' in the [{SETTINGS_SECTION}] table of {config_path}."
        )
        raise typer.Exit(code=1)

    sheet_client = GoogleSheetClient(
        spreadsheet_id=settings.spreadsheet_id,
        worksheet_name=settings.sheet_name,
        credentials_path=credentials_path,
        header_row=settings.header_row,
    )

    # On first run (no config yet) walk the user through matching their
    # worksheet headers to our fields. Non-interactive sessions fall back to the
    # built-in defaults so scripts and CI keep working.
    if setup or (not config_path.exists() and sys.stdin.isatty()):
        try:
            sheet_client.column_mapping = run_setup_wizard(
                sheet_client.get_headers(), config_path
            )
        # TODO refactor below into block
        except SetupCancelledError as exc:
            logger.error(str(exc))
            raise typer.Exit(code=1) from exc
    else:
        try:
            sheet_client.column_mapping = load_worksheet_mapping(config_path)
        except ColumnMappingError as exc:
            logger.error(str(exc))
            raise typer.Exit(code=1) from exc

    sheet_client.append_listing(property_listing)
    logger.info(
        "Adding row to the sheet with the property listing has completed successfully."
    )


def cli() -> None:
    """Console-script entry point."""
    typer.run(main)


if __name__ == "__main__":
    cli()
