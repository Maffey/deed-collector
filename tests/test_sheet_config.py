from pathlib import Path

import pytest

from deed_collector.real_estate.property_listing import PropertyListing
from deed_collector.sheet_clients.config import (
    CONFIG_SECTION,
    DEFAULT_WORKSHEET_MAPPING,
    MAPPABLE_FIELDS,
    header_to_field,
    load_worksheet_mapping,
    normalize_header,
    save_worksheet_mapping,
    validate_worksheet_mapping,
)
from deed_collector.sheet_clients.exceptions import (
    ConfigFileError,
    InvalidColumnMappingError,
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
def test_load_applies_user_values_over_defaults(tmp_path, config_body, expected_overrides):
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

    save_worksheet_mapping(path, mapping)

    assert load_worksheet_mapping(path)["price"] == 'cena "zł" \\ netto'


def test_save_writes_empty_string_for_skipped_field(tmp_path):
    path = tmp_path / "config.toml"
    mapping = {**DEFAULT_WORKSHEET_MAPPING, "area": ""}

    save_worksheet_mapping(path, mapping)

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
