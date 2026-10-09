"""User-configurable worksheet target and listing-to-column mapping.

The target worksheet settings live in a TOML ``[worksheet]`` table (all keys
optional), and the column mapping lives in a ``[worksheet_mapping]`` table::

    [worksheet]
    spreadsheet_id = "1Abc..."
    sheet_name = "Sheet1"
    header_row = 1
    comment = "Added by deed-collector"

    [worksheet_mapping]
    price = "cena (zł)"
    area = "metraż (m²)"
    comment = "Notatki"

The ``spreadsheet_id`` setting has no built-in default: it must be supplied
either here or as a CLI argument. Any CLI value takes precedence over the file.
"""

import json
import tomllib
import unicodedata
from collections.abc import Mapping
from dataclasses import dataclass, replace
from pathlib import Path

from deed_collector.sheet_clients.common import DEFAULT_SHEET_NAME
from deed_collector.sheet_clients.exceptions import (
    ConfigFileError,
    InvalidColumnMappingError,
    InvalidSheetSettingsError,
    UnknownMappingFieldError,
)

CONFIG_SECTION = "worksheet_mapping"
SETTINGS_SECTION = "worksheet"
DEFAULT_CONFIG_FILE_NAME = "config.toml"

DEFAULT_HEADER_ROW = 1

SPREADSHEET_ID_KEY = "spreadsheet_id"
SHEET_NAME_KEY = "sheet_name"
HEADER_ROW_KEY = "header_row"
COMMENT_KEY = "comment"
SHEET_SETTING_KEYS: tuple[str, ...] = (
    SPREADSHEET_ID_KEY,
    SHEET_NAME_KEY,
    HEADER_ROW_KEY,
    COMMENT_KEY,
)

# ``price_per_square_meter`` is a computed property on ``PropertyListing``
# rather than a dataclass field, which is why this list is explicit.
MAPPABLE_FIELDS: tuple[str, ...] = (
    "provider",
    "url",
    "address",
    "price",
    "area",
    "price_per_square_meter",
    "number_of_rooms",
    "market_type",
    "year_of_construction",
    "listing_creation_date",
    "comment",
)

# TODO if it goes public/popular I should probably switch to english as default :skull:
DEFAULT_WORKSHEET_MAPPING: dict[str, str] = {
    "provider": "portal",
    "url": "link do ogłoszenia",
    "address": "adres (do mapy)",
    "price": "cena (zł)",
    "area": "metraż (m²)",
    "price_per_square_meter": "cena/m² (zł)",
    "number_of_rooms": "pokoje",
    "market_type": "rynek",
    "year_of_construction": "rok budowy",
    "listing_creation_date": "Data dodania",
    "comment": "Notatki",
}


@dataclass(frozen=True)
class SheetSettings:
    """Target worksheet settings, independent of the column mapping.

    ``spreadsheet_id`` is ``None`` when it is not configured anywhere.
    """

    spreadsheet_id: str | None = None
    sheet_name: str = DEFAULT_SHEET_NAME
    header_row: int = DEFAULT_HEADER_ROW
    comment: str = ""

    def overridden_by(
        self,
        *,
        spreadsheet_id: str | None = None,
        sheet_name: str | None = None,
        header_row: int | None = None,
        comment: str | None = None,
    ) -> SheetSettings:
        """Layer explicitly provided CLI values on top of these settings.

        ``None`` means "not provided on the command line", so the file value is
        kept.
        """
        return replace(
            self,
            spreadsheet_id=(
                spreadsheet_id if spreadsheet_id is not None else self.spreadsheet_id
            ),
            sheet_name=sheet_name if sheet_name is not None else self.sheet_name,
            header_row=header_row if header_row is not None else self.header_row,
            comment=comment if comment is not None else self.comment,
        )


def normalize_header(header: str) -> str:
    """Normalize a column header for comparison.

    NFC makes composed/decomposed Polish letters compare equal, ``casefold``
    folds case, and ``split`` collapses runs of whitespace (including the
    non-breaking spaces Google Sheets sometimes returns).
    """
    return " ".join(unicodedata.normalize("NFC", header).split()).casefold()


def validate_worksheet_mapping(
    mapping: Mapping[str, object],
) -> dict[str, str]:
    # TODO I might be crazy but maybe I can apply pydantic here, instead of this.
    """Validate a ``field -> column`` mapping and return a clean copy.

    Raises:
        UnknownMappingFieldError: a key is not a field we can export.
        InvalidColumnMappingError: a value is not a string, or two fields point
            at the same worksheet column.
    """
    validated: dict[str, str] = {}
    seen_columns: dict[str, str] = {}

    for field, column in mapping.items():
        if field not in MAPPABLE_FIELDS:
            raise UnknownMappingFieldError(
                f"Unknown field {field!r} in [{CONFIG_SECTION}]. "
                f"Valid fields: {', '.join(MAPPABLE_FIELDS)}."
            )
        if not isinstance(column, str):
            raise InvalidColumnMappingError(
                f"Column for {field!r} must be a string, got {type(column).__name__}."
            )

        column = column.strip()
        if not column:
            validated[field] = ""
            continue

        normalized = normalize_header(column)
        other = seen_columns.get(normalized)
        if other is not None:
            raise InvalidColumnMappingError(
                f"Fields {other!r} and {field!r} both map to the column "
                f"{column!r}; every exported field needs its own column."
            )
        seen_columns[normalized] = field
        validated[field] = column

    return validated


def validate_sheet_settings(settings: Mapping[str, object]) -> SheetSettings:
    """Validate a ``[worksheet]`` table and return clean settings.

    Missing keys fall back to :class:`SheetSettings` defaults.

    Raises:
        InvalidSheetSettingsError: an unknown key is present, or a known key
            has a value of the wrong type or range.
    """
    unknown = sorted(set(settings) - set(SHEET_SETTING_KEYS))
    if unknown:
        raise InvalidSheetSettingsError(
            f"Unknown key(s) {', '.join(map(repr, unknown))} in [{SETTINGS_SECTION}]. "
            f"Valid keys: {', '.join(SHEET_SETTING_KEYS)}."
        )

    spreadsheet_id = settings.get(SPREADSHEET_ID_KEY)
    if spreadsheet_id is not None:
        if not isinstance(spreadsheet_id, str) or not spreadsheet_id.strip():
            raise InvalidSheetSettingsError(
                f"'{SPREADSHEET_ID_KEY}' in [{SETTINGS_SECTION}] must be a "
                "non-empty string."
            )
        spreadsheet_id = spreadsheet_id.strip()

    sheet_name = settings.get(SHEET_NAME_KEY, DEFAULT_SHEET_NAME)
    if not isinstance(sheet_name, str) or not sheet_name.strip():
        raise InvalidSheetSettingsError(
            f"'{SHEET_NAME_KEY}' in [{SETTINGS_SECTION}] must be a non-empty string."
        )
    sheet_name = sheet_name.strip()

    header_row = settings.get(HEADER_ROW_KEY, DEFAULT_HEADER_ROW)
    # ``bool`` is a subclass of ``int``, so reject it explicitly.
    if (
        isinstance(header_row, bool)
        or not isinstance(header_row, int)
        or header_row < 1
    ):
        raise InvalidSheetSettingsError(
            f"'{HEADER_ROW_KEY}' in [{SETTINGS_SECTION}] must be an integer >= 1."
        )

    comment = settings.get(COMMENT_KEY, "")
    if not isinstance(comment, str):
        raise InvalidSheetSettingsError(
            f"'{COMMENT_KEY}' in [{SETTINGS_SECTION}] must be a string."
        )
    # An empty (or whitespace-only) comment means "write nothing", so normalizing
    # it keeps the disabled state a single value.
    comment = comment.strip()

    return SheetSettings(
        spreadsheet_id=spreadsheet_id,
        sheet_name=sheet_name,
        header_row=header_row,
        comment=comment,
    )


def load_worksheet_mapping(
    config_path: Path | str = DEFAULT_CONFIG_FILE_NAME,
) -> dict[str, str]:
    """Load the worksheet mapping, falling back to defaults for missing keys.

    Only the ``[worksheet_mapping]`` table is validated, so a broken mapping can
    still be repaired interactively with ``--setup``.
    """
    path = Path(config_path)
    if not path.exists():
        return dict(DEFAULT_WORKSHEET_MAPPING)

    raw_mapping = _table(_read_config(path), CONFIG_SECTION, path)
    user_mapping = validate_worksheet_mapping(raw_mapping)
    return {**DEFAULT_WORKSHEET_MAPPING, **user_mapping}


def load_sheet_settings(
    config_path: Path | str = DEFAULT_CONFIG_FILE_NAME,
) -> SheetSettings:
    """Load the target worksheet settings, falling back to defaults.

    Only the ``[worksheet]`` table is validated; the column mapping is ignored.
    """
    path = Path(config_path)
    if not path.exists():
        return SheetSettings()

    return validate_sheet_settings(_table(_read_config(path), SETTINGS_SECTION, path))


def save_config(
    config_path: Path | str,
    *,
    settings: SheetSettings,
    mapping: Mapping[str, str],
) -> None:
    """Validate ``mapping`` and write ``settings`` + ``mapping`` as TOML.

    This writer does no merging: callers own the values, including any existing
    settings they want to carry over.
    """
    validate_worksheet_mapping(mapping)

    lines = [
        "# deed-collector configuration.",
        "#",
        "# [worksheet] sets the target spreadsheet tab. Every key is optional;",
        "# CLI values (spreadsheet id argument, --sheet-name, --header-row,",
        "# --comment) override the values written here.",
        "#",
        "# [worksheet_mapping] maps each exported field to the header of the",
        '# column it should be written to. Use "" to skip exporting a field.',
        "",
    ]

    settings_lines = _render_settings(settings)
    if settings_lines:
        lines.append(f"[{SETTINGS_SECTION}]")
        lines.extend(settings_lines)
        lines.append("")

    lines.append(f"[{CONFIG_SECTION}]")
    lines.extend(
        f"{field} = {_toml_string(mapping.get(field, ''))}" for field in MAPPABLE_FIELDS
    )
    lines.append("")

    Path(config_path).write_text("\n".join(lines), encoding="utf-8")


def header_to_field(mapping: Mapping[str, str]) -> dict[str, str]:
    """Build the normalized header -> internal field lookup used for writing."""
    return {
        normalize_header(column): field
        for field, column in mapping.items()
        if column.strip()
    }


def _read_config(path: Path) -> dict:
    try:
        with path.open("rb") as config_file:
            return tomllib.load(config_file)
    except tomllib.TOMLDecodeError as exc:
        raise ConfigFileError(f"Could not parse {path}: {exc}") from exc
    except OSError as exc:
        raise ConfigFileError(f"Could not read {path}: {exc}") from exc


def _table(config: Mapping[str, object], name: str, path: Path) -> Mapping[str, object]:
    table = config.get(name, {})
    if not isinstance(table, dict):
        raise ConfigFileError(f"[{name}] in {path} must be a table.")
    return table


def _render_settings(settings: SheetSettings) -> list[str]:
    lines: list[str] = []
    if settings.spreadsheet_id is not None:
        lines.append(f"{SPREADSHEET_ID_KEY} = {_toml_string(settings.spreadsheet_id)}")
    if settings.sheet_name != DEFAULT_SHEET_NAME:
        lines.append(f"{SHEET_NAME_KEY} = {_toml_string(settings.sheet_name)}")
    if settings.header_row != DEFAULT_HEADER_ROW:
        lines.append(f"{HEADER_ROW_KEY} = {settings.header_row}")
    if settings.comment:
        lines.append(f"{COMMENT_KEY} = {_toml_string(settings.comment)}")
    return lines


def _toml_string(value: str) -> str:
    """Render ``value`` as a TOML basic string.

    JSON string escaping is a strict subset of TOML basic-string escaping for
    the characters we care about, so ``json.dumps`` is reused to avoid rolling
    our own. Non-ASCII characters are kept intact for readability.
    """
    return json.dumps(value, ensure_ascii=False)
