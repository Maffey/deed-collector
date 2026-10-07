"""Interactive first-run creation of the worksheet column mapping.

The wizard is built on Typer's own prompt helpers so the project does not need
a third-party prompting library. Since Typer has no dropdown, the worksheet
headers are listed once and the user answers with a number.
"""

from collections.abc import Mapping, Sequence
from pathlib import Path

import typer

from deed_collector.sheet_clients.config import (
    DEFAULT_WORKSHEET_MAPPING,
    MAPPABLE_FIELDS,
    normalize_header,
    save_worksheet_mapping,
)
from deed_collector.sheet_clients.exceptions import SetupCancelledError

_SKIP_VALUES = {"", "0", "skip", "-"}


def run_setup_wizard(
    headers: Sequence[str],
    config_path: Path | str,
    *,
    defaults: Mapping[str, str] = DEFAULT_WORKSHEET_MAPPING,
) -> dict[str, str]:
    """Prompt for a column per field, then write the mapping to disk.

    ``headers`` are the user's actual worksheet headers, so they pick from the
    columns that really exist rather than typing them by hand.
    """
    columns = list(dict.fromkeys(headers))
    if not columns:
        raise SetupCancelledError(
            "The worksheet header row is empty; cannot build a column mapping."
        )

    _print_columns(columns)

    mapping: dict[str, str] = {}
    try:
        for field in MAPPABLE_FIELDS:
            mapping[field] = _ask_for_column(field, columns, defaults.get(field, ""))
    except (typer.Abort, EOFError, KeyboardInterrupt) as exc:
        raise SetupCancelledError(
            "Interactive setup was cancelled; the config file was not written."
        ) from exc

    save_worksheet_mapping(config_path, mapping)
    typer.echo(f"Saved worksheet mapping to {config_path}.")
    return mapping


def _print_columns(columns: Sequence[str]) -> None:
    typer.echo("Match each listing field to a worksheet column.")
    typer.echo("Enter a column number, a column name, or 'skip'.\n")
    for index, column in enumerate(columns, start=1):
        typer.echo(f"  {index}. {column}")
    typer.echo("")


def _ask_for_column(field: str, columns: Sequence[str], default: str) -> str:
    default_index = columns.index(default) + 1 if default in columns else None
    prompt_default = str(default_index) if default_index is not None else ""

    while True:
        raw = typer.prompt(
            f"Column for '{field}'",
            default=prompt_default,
            show_default=default_index is not None,
        )
        choice = parse_column_choice(raw, columns)
        if choice is not None:
            return choice
        typer.echo(f"Invalid choice. Enter 1-{len(columns)}, a column name, or 'skip'.")


def parse_column_choice(raw: str, columns: Sequence[str]) -> str | None:
    """Parse a wizard answer into a column name.

    Returns the matched column, ``""`` to skip, or ``None`` when the answer
    matches no column and should be re-prompted.
    """
    value = raw.strip()
    if value.casefold() in _SKIP_VALUES:
        return ""

    if value.isdigit():
        index = int(value)
        if 1 <= index <= len(columns):
            return columns[index - 1]
        return None

    normalized = normalize_header(value)
    for column in columns:
        if normalize_header(column) == normalized:
            return column
    return None
