import random
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Annotated, NoReturn

import typer
from loguru import logger

from deed_collector.real_estate.market import MarketType
from deed_collector.real_estate.property_listing import PropertyListing
from deed_collector.real_estate.providers import Provider
from deed_collector.scraper import ScraperFactory
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


def _exit_with_error(message: str, *, cause: Exception | None = None) -> NoReturn:
    """Log ``message`` as an error and abort the CLI with exit code 1."""
    logger.error(message)
    raise typer.Exit(code=1) from cause


@contextmanager
def _exit_on_error(*errors: type[Exception]) -> Iterator[None]:
    """Abort the CLI with exit code 1 if ``errors`` are raised in the block."""
    try:
        yield
    except errors as exc:
        _exit_with_error(str(exc), cause=exc)


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

    with ScraperFactory.create(url) as scraper:
        property_listing = scraper.run(url)
    logger.debug(property_listing)

    # CLI values win, then the config file, then the built-in defaults.
    with _exit_on_error(SheetConfigError):
        settings = load_sheet_settings(config_path)

    settings = settings.overridden_by(
        spreadsheet_id=spreadsheet_id,
        sheet_name=sheet_name,
        header_row=header_row,
    )
    if settings.spreadsheet_id is None:
        _exit_with_error(
            "No spreadsheet id provided. Pass it as an argument or set "
            f"'spreadsheet_id' in the [{SETTINGS_SECTION}] table of {config_path}."
        )

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
        with _exit_on_error(SetupCancelledError):
            sheet_client.column_mapping = run_setup_wizard(
                sheet_client.get_headers(), config_path
            )
    else:
        with _exit_on_error(ColumnMappingError):
            sheet_client.column_mapping = load_worksheet_mapping(config_path)

    sheet_client.append_listing(property_listing)
    logger.info(
        "Adding row to the sheet with the property listing has completed successfully."
    )


def cli() -> None:
    """Console-script entry point."""
    typer.run(main)


if __name__ == "__main__":
    cli()
