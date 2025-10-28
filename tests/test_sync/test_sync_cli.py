"""Tests for the 'fmu sync' commands."""

from collections.abc import Generator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest
from fmu.datamodels.fmu_results.fields import CountryItem
from fmu.settings import ProjectFMUDirectory
from pytest import MonkeyPatch
from typer.testing import CliRunner

from fmu_settings_cli.__main__ import app
from fmu_settings_cli.sync.model_diff import IGNORED_FIELDS

# ruff: noqa: PLR2004

runner = CliRunner()


def test_sync_cmd_with_help(patch_ensure_port: Generator[None]) -> None:
    """Tests that 'fmu sync' emits help information."""
    result = runner.invoke(app, ["sync", "--help"])

    assert result.exit_code == 0
    assert "Usage: fmu sync" in result.stdout
    assert "Sync the settings and configuration" in result.stdout
    assert "--from" in result.stdout
    assert "--to" in result.stdout


def test_sync_cmd_with_no_options() -> None:
    """Tests that 'fmu sync' errors with no options."""
    result = runner.invoke(app, ["sync"])
    assert "Missing option '--to'" in result.stderr
    assert result.exit_code == 2


def test_sync_but_no_fmu_directory(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    """Tests that running 'fmu sync' with no FMU directory nearby issues an error."""
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["sync", "--to", "foo"])
    assert "Unable to find a known and valid FMU project" in result.stderr
    assert "No .fmu directory found" in result.stderr
    assert "'cd' into the correct directory" in result.stderr
    assert "Abort" in result.stderr
    assert result.exit_code == 1


def test_sync_invalid_to_dir_config_json_raises_validation_error(
    two_fmu_revisions: tuple[Path, ProjectFMUDirectory, ProjectFMUDirectory],
    monkeypatch: MonkeyPatch,
) -> None:
    """Tests that 'fmu sync' displays a validation error if the target is invalid."""
    tmp_path, project_a, project_b = two_fmu_revisions
    monkeypatch.chdir(project_a.path.parent)

    # Make '--to' target config invalid
    project_b.config.path.write_text("invalid")
    result = runner.invoke(
        app, ["sync", "--to", str(project_b.path.parent)], input="y\n"
    )

    assert "Unable to find an FMU Settings configuration to sync to" in result.stderr
    assert (
        "Reason: Invalid JSON in resource file for 'ProjectConfigManager'"
        in result.stderr
    )
    assert result.exit_code == 1


def test_sync_invalid_to_dir_config_content_raises_validation_error(
    two_fmu_revisions: tuple[Path, ProjectFMUDirectory, ProjectFMUDirectory],
    monkeypatch: MonkeyPatch,
) -> None:
    """Tests that 'fmu sync' displays a validation error if the target is invalid."""
    tmp_path, project_a, project_b = two_fmu_revisions
    monkeypatch.chdir(project_a.path.parent)

    # Make '--to' target config invalid
    project_b.config.path.write_text('{"invalid": 1}')
    result = runner.invoke(
        app, ["sync", "--to", str(project_b.path.parent)], input="y\n"
    )
    assert "Unable to find an FMU Settings configuration to sync to" in result.stderr
    assert (
        "Reason: Invalid content in resource file for 'ProjectConfigManager"
        in result.stderr
    )
    assert "validation errors" in result.stderr
    assert result.exit_code == 1


@pytest.mark.parametrize(
    "from_flag, to_flag",
    [("--from", "--to"), ("-f", "--to"), ("-f", "-t"), ("--from", "-t")],
)
def test_sync_from_no_changes(
    two_fmu_revisions: tuple[Path, ProjectFMUDirectory, ProjectFMUDirectory],
    from_flag: str,
    to_flag: str,
) -> None:
    """Tests that 'fmu sync' uses 'from'/'to' flags and emits no changes message.

    Also sanity checks the short and long flags.
    """
    tmp_path, project_a, project_b = two_fmu_revisions
    result = runner.invoke(
        app,
        [
            "sync",
            from_flag,
            str(project_a.path.parent),
            to_flag,
            str(project_b.path.parent),
        ],
    )
    assert "No changes detected" in result.stdout
    assert result.exit_code == 0


def test_sync_no_changes_from_current_dir(
    two_fmu_revisions: tuple[Path, ProjectFMUDirectory, ProjectFMUDirectory],
    monkeypatch: MonkeyPatch,
) -> None:
    """Tests that 'fmu sync' detects nothing has changed from the current directory."""
    tmp_path, project_a, project_b = two_fmu_revisions
    monkeypatch.chdir(project_a.path.parent)
    result = runner.invoke(app, ["sync", "--to", str(project_b.path.parent)])
    assert "No changes detected" in result.stdout
    assert result.exit_code == 0


@pytest.mark.parametrize(
    "field, value",
    [
        ("created_at", datetime.now(UTC)),
        ("created_by", "foo"),
    ],
)
def test_sync_disregards_ignored_fields(
    two_fmu_revisions: tuple[Path, ProjectFMUDirectory, ProjectFMUDirectory],
    monkeypatch: MonkeyPatch,
    field: str,
    value: Any,
) -> None:
    """Tests that 'fmu sync' does not see ignored fields as changes to sync."""
    tmp_path, project_a, project_b = two_fmu_revisions
    monkeypatch.chdir(project_a.path.parent)

    assert field in IGNORED_FIELDS
    project_a.set_config_value(field, value)

    result = runner.invoke(app, ["sync", "--to", str(project_b.path.parent)])
    assert "No changes detected" in result.stdout
    assert result.exit_code == 0


def test_sync_finds_changed_value_field(
    two_fmu_revisions: tuple[Path, ProjectFMUDirectory, ProjectFMUDirectory],
    monkeypatch: MonkeyPatch,
) -> None:
    """Tests that 'fmu sync' displays and confirms a changed field.

    No is selected.
    """
    tmp_path, project_a, project_b = two_fmu_revisions
    monkeypatch.chdir(project_a.path.parent)

    project_a.set_config_value("model.name", "foo")

    result = runner.invoke(
        app, ["sync", "--to", str(project_b.path.parent)], input="n\n"
    )
    assert "Value Changes in ProjectConfig" in result.stdout
    assert "model.name" in result.stdout
    assert "foo" in result.stdout
    assert result.exit_code == 1

    # Does not update it.
    assert project_b.config.load().model.name == ""  # type: ignore[union-attr]


def test_sync_finds_changed_value_field_and_saves_after_confirm(
    two_fmu_revisions: tuple[Path, ProjectFMUDirectory, ProjectFMUDirectory],
    monkeypatch: MonkeyPatch,
) -> None:
    """Tests that 'fmu sync' displays and confirms a changed value field.

    Yes is selected.
    """
    tmp_path, project_a, project_b = two_fmu_revisions
    monkeypatch.chdir(project_a.path.parent)

    project_a.set_config_value("model.name", "foo")

    result = runner.invoke(
        app, ["sync", "--to", str(project_b.path.parent)], input="y\n"
    )
    assert "Value Changes in ProjectConfig" in result.stdout
    assert "model.name" in result.stdout
    assert "foo" in result.stdout
    assert "Complex Changes" not in result.stdout  # Not in
    assert "Success: All done!" in result.stdout
    assert result.exit_code == 0

    # Does update it.
    assert project_b.config.load(force=True).model.name == "foo"  # type: ignore[union-attr]


def test_sync_finds_changed_complex_field_and_saves_after_confirm(
    two_fmu_revisions: tuple[Path, ProjectFMUDirectory, ProjectFMUDirectory],
    monkeypatch: MonkeyPatch,
) -> None:
    """Tests that 'fmu sync' displays and confirms a changed complex (BaseModel) field.

    Yes is selected.
    """
    tmp_path, project_a, project_b = two_fmu_revisions
    monkeypatch.chdir(project_a.path.parent)

    project_b.set_config_value("masterdata", None)
    assert project_b.config.load(force=True).masterdata is None

    result = runner.invoke(
        app, ["sync", "--to", str(project_b.path.parent)], input="y\n"
    )

    assert "Value Changes in ProjectConfig" in result.stdout
    assert "masterdata" in result.stdout
    assert "None" in result.stdout
    assert "Masterdata" in result.stdout

    assert "Complex Changes" in result.stdout
    assert "Added: masterdata" in result.stdout
    assert "smda: Smda" in result.stdout
    assert "Success: All done!" in result.stdout
    assert result.exit_code == 0

    assert (
        project_b.config.load(force=True).masterdata
        == project_a.config.load().masterdata
    )


def test_sync_finds_changed_list_and_saves_after_confirm(
    two_fmu_revisions: tuple[Path, ProjectFMUDirectory, ProjectFMUDirectory],
    monkeypatch: MonkeyPatch,
) -> None:
    """Tests that 'fmu sync' detects and displays a changed list field correctly.

    Yes is selected.
    """
    tmp_path, project_a, project_b = two_fmu_revisions
    monkeypatch.chdir(project_a.path.parent)

    uuid = uuid4()
    country_item = CountryItem(identifier="Norway", uuid=uuid)
    project_a.set_config_value("masterdata.smda.country", [country_item])
    assert project_a.config.load(force=True).masterdata.smda.country[0] == country_item  # type: ignore[union-attr]

    result = runner.invoke(
        app, ["sync", "--to", str(project_b.path.parent)], input="y\n"
    )

    assert "Value Changes in ProjectConfig" in result.stdout
    assert "masterdata.smda.country" in result.stdout
    assert "[]" in result.stdout

    assert "Complex Changes" in result.stdout
    assert "Removed: masterdata.smda.country (old)" in result.stdout
    assert "1 items" in result.stdout
    assert "Added: masterdata.smda.country (new)" in result.stdout
    assert "0 items" in result.stdout
    assert result.exit_code == 0

    assert project_b.config.load(force=True).masterdata.smda.country == [country_item]  # type: ignore[union-attr]
