import sys
from dataclasses import replace
from pathlib import Path
from typing import Annotated

import httpx
import typer
from loguru import logger

from deed_collector.exceptions import DeedCollectorError
from deed_collector.scraper import ScraperFactory
from deed_collector.sheet_clients.config import (
    DEFAULT_CONFIG_FILE_NAME,
    SETTINGS_SECTION,
    load_sheet_settings,
    load_worksheet_mapping,
)
from deed_collector.sheet_clients.exceptions import MissingSpreadsheetIdError
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
    comment: Annotated[
        str | None,
        typer.Option(
            "--comment",
            help=(
                "Static text written to the comment column of every appended row. "
                "Overrides [worksheet].comment; an empty value writes nothing."
            ),
        ),
    ] = None,
    setup: Annotated[
        bool,
        typer.Option(
            "--setup",
            help="Force the interactive worksheet mapping setup, then continue.",
        ),
    ] = False,
) -> None:
    try:
        with ScraperFactory.create(url) as scraper:
            property_listing = scraper.run(url)
        # TODO A --verbose/--quiet flag?
        logger.debug(property_listing)

        # CLI values win, then the config file, then the built-in defaults.
        settings = load_sheet_settings(config_path).overridden_by(
            spreadsheet_id=spreadsheet_id,
            sheet_name=sheet_name,
            header_row=header_row,
            comment=comment,
        )
        if settings.spreadsheet_id is None:
            raise MissingSpreadsheetIdError(
                "No spreadsheet id provided. Pass it as an argument or set "
                f"'spreadsheet_id' in the [{SETTINGS_SECTION}] table of {config_path}."
            )
        property_listing = replace(property_listing, comment=settings.comment)

        sheet_client = GoogleSheetClient(
            spreadsheet_id=settings.spreadsheet_id,
            worksheet_name=settings.sheet_name,
            credentials_path=credentials_path,
            header_row=settings.header_row,
        )

        # On first run (no config yet) walk the user through matching their
        # worksheet headers to our fields. Non-interactive sessions fall back to
        # the built-in defaults so scripts and CI keep working.
        if setup or (not config_path.exists() and sys.stdin.isatty()):
            sheet_client.column_mapping = run_setup_wizard(
                sheet_client.get_headers(), config_path
            )
        else:
            sheet_client.column_mapping = load_worksheet_mapping(config_path)

        sheet_client.append_listing(property_listing)
    except DeedCollectorError as exc:
        logger.error(exc)
        raise typer.Exit(code=1) from exc
    except httpx.HTTPError as exc:
        logger.error(f"Network error: {exc}")
        raise typer.Exit(code=1) from exc

    logger.info(
        "Adding row to the sheet with the property listing has completed successfully."
    )


def cli() -> None:
    """Console-script entry point."""
    typer.run(main)


if __name__ == "__main__":
    # TODO add more providers
    cli()
