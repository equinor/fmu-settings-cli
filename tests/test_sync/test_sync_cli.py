"""Tests for the 'fmu sync' commands."""

from collections.abc import Generator
from pathlib import Path
from uuid import uuid4

import pytest
from fmu.datamodels.common import DiscoveryItem
from fmu.settings import ProjectFMUDirectory
from pytest import MonkeyPatch
from typer.testing import CliRunner

from fmu_settings_cli.__main__ import app

# ruff: noqa: PLR2004

runner = CliRunner()


def test_sync_cmd_with_help(patch_ensure_port: Generator[None]) -> None:
    """Tests that 'fmu sync' emits help information."""
    result = runner.invoke(app, ["sync", "--help"])

    assert result.exit_code == 0
    assert "Usage: fmu sync" in result.stdout
    assert "Sync the contents of the .fmu folder" in result.stdout
    assert "--from" in result.stdout
    assert "--to" in result.stdout
    assert "current directory" in result.stdout
    assert "bound method PathBase.cwd" not in result.stdout


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

    assert (
        "Unable to load .fmu resources for the revisions you are syncing"
        in result.stderr
    )
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
    assert (
        "Unable to load .fmu resources for the revisions you are syncing"
        in result.stderr
    )
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
    assert "Value Changes in config" in result.stdout
    assert "_changelog" not in result.stdout
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
    assert "Value Changes in config" in result.stdout
    assert "_changelog" not in result.stdout
    assert "model.name" in result.stdout
    assert "foo" in result.stdout
    assert "Success: All done!" in result.stdout
    assert str(project_a.path.parent.absolute()) in result.stdout.replace("\n", "")
    assert str(project_b.path.parent.absolute()) in result.stdout.replace("\n", "")
    assert result.exit_code == 0

    # Does update it.
    assert project_b.config.load(force=True).model.name == "foo"  # type: ignore[union-attr]


def test_sync_changelog_only_is_merged_without_being_displayed(
    two_fmu_revisions: tuple[Path, ProjectFMUDirectory, ProjectFMUDirectory],
    monkeypatch: MonkeyPatch,
) -> None:
    """Tests that changelog-only differences are synced but not rendered."""
    tmp_path, project_a, project_b = two_fmu_revisions
    monkeypatch.chdir(project_a.path.parent)

    target_changelog_size = len(project_b.changelog.load())
    project_a.changelog.log_copy_revision_to_changelog(project_a.base_path)

    result = runner.invoke(
        app, ["sync", "--to", str(project_b.path.parent)], input="y\n"
    )

    assert "Value Changes in _changelog" not in result.stdout
    assert "Complex Changes in _changelog" not in result.stdout
    assert "Success: All done!" in result.stdout
    assert result.exit_code == 0

    target_changelog = project_b.changelog.load(force=True)
    assert len(target_changelog) == target_changelog_size + 2
    assert target_changelog[-2].change_type == "copy"
    assert target_changelog[-2].path == project_a.base_path


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

    assert "Value Changes in config" in result.stdout
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
    discovery_item = DiscoveryItem(short_identifier="DROGON", uuid=uuid)
    project_a.set_config_value("masterdata.smda.discovery", [discovery_item])
    project_b.set_config_value("masterdata.smda.discovery", [])
    source_config = project_a.config.load(force=True)
    assert source_config.masterdata is not None
    assert source_config.masterdata.smda.discovery[0] == discovery_item

    result = runner.invoke(
        app, ["sync", "--to", str(project_b.path.parent)], input="y\n"
    )

    assert "Value Changes in config" in result.stdout
    assert "masterdata.smda.discovery" in result.stdout
    assert "[]" in result.stdout

    assert "Complex Changes" in result.stdout
    assert "Removed: masterdata.smda.discovery (old)" in result.stdout
    assert "1 items" in result.stdout
    assert "Added: masterdata.smda.discovery (new)" in result.stdout
    assert "0 items" in result.stdout
    assert result.exit_code == 0

    target_config = project_b.config.load(force=True)
    assert target_config.masterdata is not None
    assert target_config.masterdata.smda.discovery == [discovery_item]
