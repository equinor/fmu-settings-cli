"""Tests 'fmu init' functionality."""

from collections.abc import Callable
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
import yaml
from fmu.datamodels.fmu_results.global_configuration import GlobalConfiguration
from fmu.settings import find_nearest_fmu_directory
from fmu.settings._init import REQUIRED_FMU_PROJECT_SUBDIRS, is_fmu_project
from pydantic import ValidationError
from typer.testing import CliRunner

from fmu_settings_cli.__main__ import app
from fmu_settings_cli.init.cli import _find_global_config_source

runner = CliRunner()


@pytest.mark.parametrize(
    "dirs, expected",
    [
        (["foo"], (False, list(REQUIRED_FMU_PROJECT_SUBDIRS))),
        (["foo/ert"], (False, list(REQUIRED_FMU_PROJECT_SUBDIRS))),
        (["ertt"], (False, list(REQUIRED_FMU_PROJECT_SUBDIRS))),
        (REQUIRED_FMU_PROJECT_SUBDIRS, (True, [])),
    ],
)
def test_is_fmu_project(
    dirs: list[str], expected: tuple[bool, list[str]], in_tmp_path: Path
) -> None:
    """Tests is_fmu_project."""
    for dir_ in dirs:
        (in_tmp_path / dir_).mkdir(parents=True, exist_ok=True)

    assert is_fmu_project(in_tmp_path) == expected


def test_init_creates_user_fmu_if_exist(in_tmp_path: Path) -> None:
    """Tests that 'fmu init' does not fail creating a user .fmu/ dir if it exists."""
    home = in_tmp_path / "user"
    home.mkdir()
    (home / ".fmu").mkdir()

    with patch("pathlib.Path.home", return_value=home):
        result = runner.invoke(app, ["init"])

    assert result.exit_code == 1
    stderr = " ".join(result.stderr.split())
    missing_dirs = ", ".join(
        f"'{dir_name}'" for dir_name in REQUIRED_FMU_PROJECT_SUBDIRS
    )
    assert "Failed initializing .fmu directory." in stderr
    assert f"Did not find: {missing_dirs}." in stderr
    assert (home / ".fmu").exists()


def test_init_checks_if_fmu_dir_fails(in_tmp_path: Path) -> None:
    """Tests that 'fmu init' checks if the directory has required subdirectories."""
    result = runner.invoke(app, ["init"])
    assert result.exit_code == 1
    stderr = " ".join(result.stderr.split())
    missing_dirs = ", ".join(
        f"'{dir_name}'" for dir_name in REQUIRED_FMU_PROJECT_SUBDIRS
    )
    assert "Failed initializing .fmu directory." in stderr
    assert f"Did not find: {missing_dirs}." in stderr


def test_init_checks_if_fmu_dir_passes(in_tmp_path: Path) -> None:
    """Tests that 'fmu init' checks if the directory has required subdirectories."""
    for dir_ in REQUIRED_FMU_PROJECT_SUBDIRS:
        (in_tmp_path / dir_).mkdir(parents=True, exist_ok=True)
    fmu_dir = in_tmp_path / ".fmu"
    assert fmu_dir.exists() is False

    result = runner.invoke(app, ["init"])
    assert result.exit_code == 0
    assert "Success: All done!" in result.stdout
    assert fmu_dir.exists() is True


def test_init_does_not_check_if_fmu_dir_is_forced(in_tmp_path: Path) -> None:
    """Tests that 'fmu init --force' doesn't check if the dir has required subdirs."""
    fmu_dir = in_tmp_path / ".fmu"
    assert fmu_dir.exists() is False
    result = runner.invoke(app, ["init", "--force"])
    assert result.exit_code == 0
    assert fmu_dir.exists() is True


def test_init_looks_for_global_config(in_fmu_project: Path) -> None:
    """Tests that 'fmu init' checks if the directory has required subdirectories."""
    with patch(
        "fmu_settings_cli.init.cli.find_global_config"
    ) as mock_find_global_config:
        result = runner.invoke(app, ["init"])
        mock_find_global_config.assert_called_once_with(in_fmu_project)

    assert result.exit_code == 0


def test_init_adds_global_variables_without_masterdata(
    in_fmu_project: Path,
    global_variables_without_masterdata: dict[str, Any],
) -> None:
    """Tests that 'fmu init' fails creating a .fmu if the config has no masterdata."""
    tmp_path = in_fmu_project
    fmuconfig_out = tmp_path / "fmuconfig/output"
    fmuconfig_out.mkdir(parents=True, exist_ok=True)

    (fmuconfig_out / "global_variables.yml").write_text(
        yaml.safe_dump(global_variables_without_masterdata)
    )

    result = runner.invoke(app, ["init"])
    assert result.exit_code == 0

    assert "Warning: Unable to import masterdata" in result.stderr
    assert (
        "Reason: Validation of the global config/global variables failed."
        in result.stderr
    )
    assert "access: Field required" in result.stderr
    assert "masterdata: Field required" in result.stderr
    assert "model: Field required" in result.stderr
    assert "Success: All done!" in result.stdout

    fmu_dir = find_nearest_fmu_directory()
    fmu_dir_cfg = fmu_dir.config.load()
    assert fmu_dir_cfg.masterdata is None
    assert fmu_dir_cfg.access is None
    assert fmu_dir_cfg.model is None


def test_init_adds_global_variables_with_masterdata(
    in_fmu_project: Path,
    generate_strict_valid_globalconfiguration: Callable[[], GlobalConfiguration],
) -> None:
    """Tests that 'fmu init' adds masterdata if it does exist."""
    tmp_path = in_fmu_project

    valid_global_cfg = generate_strict_valid_globalconfiguration()

    fmuconfig_out = tmp_path / "fmuconfig/output"
    fmuconfig_out.mkdir(parents=True, exist_ok=True)

    (fmuconfig_out / "global_variables.yml").write_text(
        yaml.dump(valid_global_cfg.model_dump(mode="json", by_alias=True))
    )

    result = runner.invoke(app, ["init"])
    assert result.exit_code == 0
    stdout = " ".join(result.stdout.split())
    assert "Success: Successfully imported access, masterdata, model from" in stdout
    assert "Success: All done!" in stdout
    assert "Info: Project stratigraphy was not imported by 'fmu init'." in stdout
    assert "Open 'fmu settings' to import stratigraphy from RMS" in stdout
    assert _find_global_config_source(tmp_path) == (
        fmuconfig_out / "global_variables.yml"
    )

    fmu_dir = find_nearest_fmu_directory()
    fmu_dir_cfg = fmu_dir.config.load()
    assert fmu_dir_cfg.masterdata == valid_global_cfg.masterdata
    assert fmu_dir_cfg.access is not None
    assert fmu_dir_cfg.model is not None


def test_init_adds_input_global_config_with_masterdata(
    in_fmu_project: Path,
    generate_strict_valid_globalconfiguration: Callable[[], GlobalConfiguration],
) -> None:
    """Tests that 'fmu init' reports the input config file it imported from."""
    tmp_path = in_fmu_project

    valid_global_cfg = generate_strict_valid_globalconfiguration()

    fmuconfig_in = tmp_path / "fmuconfig/input"
    fmuconfig_in.mkdir(parents=True, exist_ok=True)
    global_config_path = fmuconfig_in / "global_master_config.yml"
    global_config_path.write_text(
        yaml.dump(valid_global_cfg.model_dump(mode="json", by_alias=True))
    )

    result = runner.invoke(app, ["init"])
    assert result.exit_code == 0
    stdout = " ".join(result.stdout.split())
    assert "Success: Successfully imported access, masterdata, model from" in stdout
    assert "Success: All done!" in stdout
    assert _find_global_config_source(tmp_path) == global_config_path


def test_init_raises_when_import_drogon_masterdata(
    in_fmu_project: Path, global_variables_with_masterdata: dict[str, Any]
) -> None:
    """Tests that 'fmu init' warns when importing Drogon masterdata."""
    tmp_path = in_fmu_project

    fmuconfig_out = tmp_path / "fmuconfig/output"
    fmuconfig_out.mkdir(parents=True, exist_ok=True)

    (fmuconfig_out / "global_variables.yml").write_text(
        yaml.dump(global_variables_with_masterdata)
    )

    result = runner.invoke(app, ["init"])
    assert result.exit_code == 0
    stderr = " ".join(result.stderr.split())
    assert "Warning: Unable to import masterdata" in result.stderr
    assert (
        "Reason: The global config contains data that is not valid SMDA "
        "masterdata." in stderr
    )
    assert "placeholder values or Drogon data" in stderr
    assert "Success: All done!" in result.stdout

    fmu_dir = find_nearest_fmu_directory()
    fmu_dir_cfg = fmu_dir.config.load()
    assert fmu_dir_cfg.masterdata is None
    assert fmu_dir_cfg.access is None
    assert fmu_dir_cfg.model is None


def test_init_fmu_dir_exists_error(in_fmu_project: Path) -> None:
    """Tests that .fmu already existing gives error."""
    fmu_dir = in_fmu_project / ".fmu"
    fmu_dir.mkdir()

    result = runner.invoke(app, ["init"])
    assert result.exit_code == 1
    assert "Error: Unable to create .fmu directory" in result.stderr
    assert ".fmu already exists" in result.stderr
    assert "You do not need to initialize a .fmu in this directory." in result.stderr
    assert "Aborted." in result.stderr


def test_init_fmu_path_exists_but_is_not_directory(in_fmu_project: Path) -> None:
    """Tests that a non-directory .fmu path gives a specific error."""
    fmu_path = in_fmu_project / ".fmu"
    fmu_path.write_text("not a directory")

    result = runner.invoke(app, ["init"])
    stderr = "".join(result.stderr.split())

    assert result.exit_code == 1
    assert "Error: Unable to create .fmu directory" in result.stderr
    assert f"{fmu_path} exists but is not a directory".replace(" ", "") in stderr
    assert "Delete this file before initializing .fmu." in result.stderr
    assert "Aborted." in result.stderr


def test_init_fmu_dir_exists_skips_global_config_messages(
    in_fmu_project: Path,
    generate_strict_valid_globalconfiguration: Callable[[], GlobalConfiguration],
) -> None:
    """Tests that existing .fmu errors do not emit unrelated import messages."""
    (in_fmu_project / ".fmu").mkdir()

    valid_global_cfg = generate_strict_valid_globalconfiguration()
    fmuconfig_out = in_fmu_project / "fmuconfig/output"
    fmuconfig_out.mkdir(parents=True, exist_ok=True)
    (fmuconfig_out / "global_variables.yml").write_text(
        yaml.dump(valid_global_cfg.model_dump(mode="json", by_alias=True))
    )

    result = runner.invoke(app, ["init"])

    assert result.exit_code == 1
    assert "Successfully imported" not in result.stdout
    assert "Unable to import masterdata" not in result.stderr
    assert ".fmu already exists" in result.stderr


def test_init_fmu_dir_no_permissions_error(in_fmu_project: Path) -> None:
    """Tests that lacking permissions to create .fmu gives error."""
    with patch(
        "fmu_settings_cli.init.cli.init_fmu_directory", side_effect=PermissionError
    ):
        result = runner.invoke(app, ["init"])
    assert result.exit_code == 1
    assert "Error: Unable to create .fmu directory" in result.stderr
    assert "lacking permissions to create" in result.stderr
    assert "Aborted." in result.stderr


def test_init_fmu_dir_validation_error(in_fmu_project: Path) -> None:
    """Tests that validation error when creating .fmu is caught.

    This should never happen unless there's a race condition.
    """
    with patch(
        "fmu_settings_cli.init.cli.init_fmu_directory",
        side_effect=ValidationError("Foo", []),
    ):
        result = runner.invoke(app, ["init"])
    assert result.exit_code == 1

    assert "Error: Unable to create .fmu directory" in result.stderr
    assert "Aborted." in result.stderr


def test_init_fmu_dir_some_error(in_fmu_project: Path) -> None:
    """Tests that .fmu already existing gives error."""
    with patch(
        "fmu_settings_cli.init.cli.init_fmu_directory",
        side_effect=ValueError("Foo"),
    ):
        result = runner.invoke(app, ["init"])
    assert result.exit_code == 1

    assert "Error: Unable to create .fmu directory" in result.stderr
    assert "Reason: Foo" in result.stderr
    assert "Please report this as a bug" in result.stderr
    assert "Aborted." in result.stderr
