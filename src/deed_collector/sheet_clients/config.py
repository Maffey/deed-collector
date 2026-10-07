"""User-configurable mapping from listing fields to worksheet columns.

The mapping lives in a TOML file under the ``[worksheet_mapping]`` table and
points *from* our internal field names *to* the header text the user has in
their spreadsheet, for example:

    [worksheet_mapping]
    price = "cena (zł)"
    area = "metraż (m²)"
"""

import json
import tomllib
import unicodedata
from collections.abc import Mapping
from pathlib import Path

from deed_collector.sheet_clients.exceptions import (
    ConfigFileError,
    InvalidColumnMappingError,
    UnknownMappingFieldError,
)

CONFIG_SECTION = "worksheet_mapping"
DEFAULT_CONFIG_FILE_NAME = "config.toml"

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
}


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


def load_worksheet_mapping(
    config_path: Path | str = DEFAULT_CONFIG_FILE_NAME,
) -> dict[str, str]:
    """Load the worksheet mapping, falling back to defaults for missing keys.

    A missing file yields :data:`DEFAULT_WORKSHEET_MAPPING` unchanged. When the
    file exists, its ``[worksheet_mapping]`` values are layered on top of the
    defaults, so users only have to spell out what differs.
    """
    path = Path(config_path)
    if not path.exists():
        return dict(DEFAULT_WORKSHEET_MAPPING)

    try:
        with path.open("rb") as config_file:
            config = tomllib.load(config_file)
    except tomllib.TOMLDecodeError as exc:
        raise ConfigFileError(f"Could not parse {path}: {exc}") from exc
    except OSError as exc:
        raise ConfigFileError(f"Could not read {path}: {exc}") from exc

    raw_mapping = config.get(CONFIG_SECTION, {})
    if not isinstance(raw_mapping, dict):
        raise ConfigFileError(
            f'[{CONFIG_SECTION}] in {path} must be a table of field = "column" pairs.'
        )

    user_mapping = validate_worksheet_mapping(raw_mapping)
    return {**DEFAULT_WORKSHEET_MAPPING, **user_mapping}


def save_worksheet_mapping(
    config_path: Path | str,
    mapping: Mapping[str, str],
) -> None:
    """Write ``mapping`` to ``config_path`` as a commented TOML file."""
    validate_worksheet_mapping(mapping)

    lines = [
        "# deed-collector worksheet column mapping.",
        "#",
        "# Each entry maps a scraped listing field to the header of the column",
        '# it should be written to. Use "" to skip exporting a field.',
        "",
        f"[{CONFIG_SECTION}]",
    ]
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


def _toml_string(value: str) -> str:
    """Render ``value`` as a TOML basic string.

    JSON string escaping is a strict subset of TOML basic-string escaping for
    the characters we care about, so ``json.dumps`` is reused to avoid rolling
    our own. Non-ASCII characters are kept intact for readability.
    """
    return json.dumps(value, ensure_ascii=False)
