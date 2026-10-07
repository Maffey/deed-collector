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


def write_config(tmp_path: Path, body: str) -> Path:
    path = tmp_path / "config.toml"
    path.write_text(body, encoding="utf-8")
    return path


def test_normalize_header_folds_case_and_collapses_whitespace():
    assert normalize_header("  Cena (ZŁ)  ") == "cena (zł)"
    assert normalize_header("cena\u00a0(zł)") == "cena (zł)"


def test_normalize_header_treats_composed_and_decomposed_letters_equally():
    composed = "adres \u0141\u00f3d\u017a"  # ó with acute, ź with acute
    decomposed = "adres Ło\u0301dz\u0301"

    assert normalize_header(composed) == normalize_header(decomposed)


def test_load_missing_file_returns_defaults(tmp_path):
    assert (
        load_worksheet_mapping(tmp_path / "missing.toml") == DEFAULT_WORKSHEET_MAPPING
    )


def test_load_partial_config_layers_over_defaults(tmp_path):
    path = write_config(
        tmp_path,
        f'[{CONFIG_SECTION}]\nprice = "cena"\n',
    )

    mapping = load_worksheet_mapping(path)

    assert mapping["price"] == "cena"
    assert mapping["url"] == DEFAULT_WORKSHEET_MAPPING["url"]


def test_load_empty_value_disables_field(tmp_path):
    path = write_config(
        tmp_path,
        f'[{CONFIG_SECTION}]\nyear_of_construction = ""\n',
    )

    assert load_worksheet_mapping(path)["year_of_construction"] == ""


def test_load_strips_surrounding_whitespace(tmp_path):
    path = write_config(
        tmp_path,
        f'[{CONFIG_SECTION}]\nprice = "  cena (zł)  "\n',
    )

    assert load_worksheet_mapping(path)["price"] == "cena (zł)"


def test_load_unknown_field_raises(tmp_path):
    path = write_config(tmp_path, f'[{CONFIG_SECTION}]\ntypo = "x"\n')

    with pytest.raises(UnknownMappingFieldError, match="typo"):
        load_worksheet_mapping(path)


def test_load_non_string_column_raises(tmp_path):
    path = write_config(tmp_path, f"[{CONFIG_SECTION}]\nprice = 123\n")

    with pytest.raises(InvalidColumnMappingError, match="price"):
        load_worksheet_mapping(path)


def test_load_duplicate_columns_raise(tmp_path):
    path = write_config(
        tmp_path,
        f'[{CONFIG_SECTION}]\nprice = "wartosc"\narea = "WARTOSC"\n',
    )

    with pytest.raises(InvalidColumnMappingError, match="every exported field"):
        load_worksheet_mapping(path)


def test_load_malformed_toml_raises_config_file_error(tmp_path):
    path = write_config(tmp_path, f"[{CONFIG_SECTION}\nprice = 'x'\n")

    with pytest.raises(ConfigFileError):
        load_worksheet_mapping(path)


def test_load_non_table_section_raises(tmp_path):
    path = write_config(tmp_path, f'{CONFIG_SECTION} = "nope"\n')

    with pytest.raises(ConfigFileError, match=CONFIG_SECTION):
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
