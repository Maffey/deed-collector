import pytest

from deed_collector.sheet_clients import setup as sheet_setup
from deed_collector.sheet_clients.config import (
    DEFAULT_WORKSHEET_MAPPING,
    MAPPABLE_FIELDS,
    SheetSettings,
    load_sheet_settings,
    load_worksheet_mapping,
    save_config,
)
from deed_collector.sheet_clients.exceptions import SetupCancelledError


def _silence_output(monkeypatch) -> None:
    monkeypatch.setattr(sheet_setup.typer, "echo", lambda *a, **k: None)


def test_run_setup_wizard_writes_selected_mapping(tmp_path, monkeypatch):
    # Answers follow MAPPABLE_FIELDS order; numbers index into the columns below.
    answers = iter(["", "", "2", "1", "3", "", "4", "", "5", "", ""])
    monkeypatch.setattr(
        sheet_setup.typer, "prompt", lambda message, **kwargs: next(answers)
    )
    _silence_output(monkeypatch)

    path = tmp_path / "config.toml"
    mapping = sheet_setup.run_setup_wizard(
        ["cena", "adres", "metraż", "pokoje", "rok"], path
    )

    assert load_worksheet_mapping(path) == mapping
    assert mapping["price"] == "cena"
    assert mapping["url"] == ""
    assert mapping["address"] == "adres"
    assert mapping["number_of_rooms"] == "pokoje"


def test_run_setup_wizard_preserves_existing_settings(tmp_path, monkeypatch):
    path = tmp_path / "config.toml"
    settings = SheetSettings(
        spreadsheet_id="abc123", sheet_name="Tracker", header_row=3
    )
    save_config(path, settings=settings, mapping=DEFAULT_WORKSHEET_MAPPING)

    monkeypatch.setattr(
        sheet_setup.typer, "prompt", lambda message, **kwargs: kwargs["default"]
    )
    _silence_output(monkeypatch)

    sheet_setup.run_setup_wizard(list(DEFAULT_WORKSHEET_MAPPING.values()), path)

    assert load_sheet_settings(path) == settings


def test_run_setup_wizard_prompts_every_field_with_default_preselected(
    tmp_path, monkeypatch
):
    prompts: list[tuple[str, object]] = []

    def fake_prompt(message, **kwargs):
        prompts.append((message, kwargs.get("default")))
        return kwargs["default"]

    monkeypatch.setattr(sheet_setup.typer, "prompt", fake_prompt)
    _silence_output(monkeypatch)

    headers = list(DEFAULT_WORKSHEET_MAPPING.values())
    mapping = sheet_setup.run_setup_wizard(headers, tmp_path / "config.toml")

    assert len(prompts) == len(MAPPABLE_FIELDS)
    for field, (_, default) in zip(MAPPABLE_FIELDS, prompts, strict=True):
        expected_index = headers.index(DEFAULT_WORKSHEET_MAPPING[field]) + 1
        assert default == str(expected_index)
    assert mapping == DEFAULT_WORKSHEET_MAPPING


def test_run_setup_wizard_deduplicates_headers(tmp_path, monkeypatch):
    messages: list[str] = []
    monkeypatch.setattr(sheet_setup.typer, "prompt", lambda message, **kwargs: "")
    monkeypatch.setattr(
        sheet_setup.typer, "echo", lambda message="", **k: messages.append(message)
    )

    sheet_setup.run_setup_wizard(["cena", "cena", "adres"], tmp_path / "config.toml")

    assert "  1. cena" in messages
    assert "  2. adres" in messages
    assert "  2. cena" not in messages


def test_run_setup_wizard_reprompts_on_invalid_answer(tmp_path, monkeypatch):
    answers = iter(["banana", *[""] * len(MAPPABLE_FIELDS)])
    monkeypatch.setattr(
        sheet_setup.typer, "prompt", lambda message, **kwargs: next(answers)
    )
    messages: list[str] = []
    monkeypatch.setattr(
        sheet_setup.typer, "echo", lambda message="", **k: messages.append(message)
    )

    mapping = sheet_setup.run_setup_wizard(["cena"], tmp_path / "config.toml")

    assert set(mapping.values()) == {""}
    assert any("Invalid choice" in message for message in messages)


def test_run_setup_wizard_cancellation_writes_nothing(tmp_path, monkeypatch):
    def abort(message, **kwargs):
        raise sheet_setup.typer.Abort

    monkeypatch.setattr(sheet_setup.typer, "prompt", abort)
    _silence_output(monkeypatch)

    path = tmp_path / "config.toml"

    with pytest.raises(SetupCancelledError):
        sheet_setup.run_setup_wizard(["cena"], path)

    assert not path.exists()


def test_run_setup_wizard_rejects_empty_header_row(tmp_path, monkeypatch):
    _silence_output(monkeypatch)

    with pytest.raises(SetupCancelledError, match="empty"):
        sheet_setup.run_setup_wizard([], tmp_path / "config.toml")


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("", ""),
        ("skip", ""),
        ("SKIP", ""),
        ("0", ""),
        ("-", ""),
        ("2", "adres"),
        ("9", None),
        ("adres", "adres"),
        ("  ADRES  ", "adres"),
        ("banana", None),
    ],
)
def test_parse_column_choice(raw, expected):
    assert sheet_setup.parse_column_choice(raw, ["cena", "adres", "metraż"]) == expected
