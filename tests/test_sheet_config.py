from pathlib import Path

import pytest

from deed_collector.real_estate.property_listing import PropertyListing
from deed_collector.sheet_clients.config import (
    CONFIG_SECTION,
    DEFAULT_WORKSHEET_MAPPING,
    MAPPABLE_FIELDS,
    SETTINGS_SECTION,
    SheetSettings,
    header_to_field,
    load_sheet_settings,
    load_worksheet_mapping,
    normalize_header,
    save_config,
    validate_worksheet_mapping,
)
from deed_collector.sheet_clients.exceptions import (
    ConfigFileError,
    InvalidColumnMappingError,
    InvalidSheetSettingsError,
    UnknownMappingFieldError,
)


def write_config(tmp_path: Path, config_body: str) -> Path:
    path = tmp_path / "config.toml"
    path.write_text(config_body, encoding="utf-8")
    return path


@pytest.mark.parametrize(
    ("header", "expected"),
    [
        ("  Cena (ZŁ)  ", "cena (zł)"),
        ("cena\u00a0(zł)", "cena (zł)"),
        ("adres \u0141\u00f3d\u017a", "adres łódź"),
        ("adres Ło\u0301dz\u0301", "adres łódź"),
    ],
)
def test_normalize_header(header, expected):
    assert normalize_header(header) == expected


def test_load_missing_file_returns_defaults(tmp_path):
    assert (
        load_worksheet_mapping(tmp_path / "missing.toml") == DEFAULT_WORKSHEET_MAPPING
    )


@pytest.mark.parametrize(
    ("config_body", "expected_overrides"),
    [
        ('price = "cena"', {"price": "cena"}),
        ('year_of_construction = ""', {"year_of_construction": ""}),
        ('price = "  cena (zł)  "', {"price": "cena (zł)"}),
    ],
)
def test_load_applies_user_values_over_defaults(
    tmp_path, config_body, expected_overrides
):
    path = write_config(tmp_path, f"[{CONFIG_SECTION}]\n{config_body}\n")

    mapping = load_worksheet_mapping(path)

    assert mapping == {**DEFAULT_WORKSHEET_MAPPING, **expected_overrides}


@pytest.mark.parametrize(
    ("config_body", "exception", "match"),
    [
        (f'[{CONFIG_SECTION}]\ntypo = "x"', UnknownMappingFieldError, "typo"),
        (f"[{CONFIG_SECTION}]\nprice = 123", InvalidColumnMappingError, "price"),
        (
            f'[{CONFIG_SECTION}]\nprice = "wartosc"\narea = "WARTOSC"',
            InvalidColumnMappingError,
            "every exported field",
        ),
        (f"[{CONFIG_SECTION}\nprice = 'x'", ConfigFileError, None),
        (f'{CONFIG_SECTION} = "nope"', ConfigFileError, CONFIG_SECTION),
    ],
)
def test_load_rejects_invalid_config(tmp_path, config_body, exception, match):
    path = write_config(tmp_path, config_body)

    with pytest.raises(exception, match=match):
        load_worksheet_mapping(path)


def test_save_then_load_round_trips_unicode(tmp_path):
    path = tmp_path / "config.toml"
    mapping = {**DEFAULT_WORKSHEET_MAPPING, "price": 'cena "zł" \\ netto'}

    save_config(path, settings=SheetSettings(), mapping=mapping)

    assert load_worksheet_mapping(path)["price"] == 'cena "zł" \\ netto'


def test_save_writes_empty_string_for_skipped_field(tmp_path):
    path = tmp_path / "config.toml"
    mapping = {**DEFAULT_WORKSHEET_MAPPING, "area": ""}

    save_config(path, settings=SheetSettings(), mapping=mapping)

    assert 'area = ""' in path.read_text(encoding="utf-8")


def test_validate_rejects_unknown_field():
    with pytest.raises(UnknownMappingFieldError):
        validate_worksheet_mapping({"nope": "x"})


def test_header_to_field_skips_disabled_columns():
    lookup = header_to_field({**DEFAULT_WORKSHEET_MAPPING, "year_of_construction": ""})

    assert lookup[normalize_header("cena (zł)")] == "price"
    assert normalize_header("rok budowy") not in lookup


def test_mappable_fields_exist_on_property_listing():
    for field in MAPPABLE_FIELDS:
        assert hasattr(PropertyListing, field), field


def test_default_mapping_covers_every_mappable_field():
    assert set(DEFAULT_WORKSHEET_MAPPING) == set(MAPPABLE_FIELDS)


def test_load_settings_defaults_when_missing(tmp_path):
    assert load_sheet_settings(tmp_path / "missing.toml") == SheetSettings()


def test_load_settings_from_file(tmp_path):
    path = write_config(
        tmp_path,
        f"[{SETTINGS_SECTION}]\n"
        'spreadsheet_id = "  abc123  "\n'
        'sheet_name = "Tracker"\n'
        "header_row = 4\n",
    )

    assert load_sheet_settings(path) == SheetSettings(
        spreadsheet_id="abc123", sheet_name="Tracker", header_row=4
    )


@pytest.mark.parametrize(
    ("config_body", "exception"),
    [
        (f'[{SETTINGS_SECTION}]\ntypo = "x"', InvalidSheetSettingsError),
        (f"[{SETTINGS_SECTION}]\nsheet_name = 5", InvalidSheetSettingsError),
        (f"[{SETTINGS_SECTION}]\nheader_row = 0", InvalidSheetSettingsError),
        (f'{SETTINGS_SECTION} = "nope"', ConfigFileError),
    ],
)
def test_load_rejects_invalid_settings(tmp_path, config_body, exception):
    path = write_config(tmp_path, config_body)

    with pytest.raises(exception):
        load_sheet_settings(path)


def test_overridden_by_prefers_cli_values():
    settings = SheetSettings(
        spreadsheet_id="from-file", sheet_name="File", header_row=2
    )

    merged = settings.overridden_by(
        spreadsheet_id="from-cli", sheet_name="CLI", header_row=7
    )

    assert merged == SheetSettings(
        spreadsheet_id="from-cli", sheet_name="CLI", header_row=7
    )
    assert settings.overridden_by() == settings


def test_save_config_round_trips_settings(tmp_path):
    path = tmp_path / "config.toml"
    settings = SheetSettings(
        spreadsheet_id="abc123", sheet_name="Tracker", header_row=3
    )

    save_config(path, settings=settings, mapping=DEFAULT_WORKSHEET_MAPPING)

    assert load_sheet_settings(path) == settings
    assert load_worksheet_mapping(path) == DEFAULT_WORKSHEET_MAPPING
