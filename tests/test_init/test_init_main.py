"""Tests 'fmu init' functionality."""

import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
import yaml
from fmu.datamodels.fmu_results.global_configuration import GlobalConfiguration
from fmu.settings import find_nearest_fmu_directory
from pytest import CaptureFixture

from fmu_settings_cli.__main__ import main
from fmu_settings_cli.init.main import REQUIRED_FMU_PROJECT_SUBDIRS, is_fmu_project


@pytest.mark.parametrize(
    "dirs, expected",
    [
        (["foo"], (False, REQUIRED_FMU_PROJECT_SUBDIRS)),
        (["foo/ert"], (False, REQUIRED_FMU_PROJECT_SUBDIRS)),
        (["ertt"], (False, REQUIRED_FMU_PROJECT_SUBDIRS)),
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


def test_init_creates_user_fmu_if_not_exist(
    tmp_path: Path, capsys: CaptureFixture[str]
) -> None:
    """Tests that 'fmu init' creates a user .fmu/ dir."""
    home = tmp_path / "user"
    home.mkdir()

    with (
        patch.object(sys, "argv", ["fmu", "init"]),
        patch("pathlib.Path.home", return_value=home),
        pytest.raises(SystemExit, match="1"),
    ):
        main()

    captured = capsys.readouterr()
    stderr = captured.err.replace("\n", " ").replace("  ", " ")
    assert "does not appear to be an FMU project" in stderr
    assert "ert" in stderr
    assert (home / ".fmu").exists()


def test_init_creates_user_fmu_if_exist(
    tmp_path: Path, capsys: CaptureFixture[str]
) -> None:
    """Tests that 'fmu init' does not fail creating a user .fmu/ dir if it exists."""
    home = tmp_path / "user"
    home.mkdir()
    (home / ".fmu").mkdir()

    with (
        patch.object(sys, "argv", ["fmu", "init"]),
        patch("pathlib.Path.home", return_value=home),
        pytest.raises(SystemExit, match="1"),
    ):
        main()

    captured = capsys.readouterr()
    stderr = captured.err.replace("\n", " ").replace("  ", " ")
    assert "does not appear to be an FMU project" in stderr
    assert "ert" in stderr
    assert (home / ".fmu").exists()


def test_init_checks_if_fmu_dir_fails(
    tmp_path: Path, capsys: CaptureFixture[str]
) -> None:
    """Tests that 'fmu init' checks if the directory has required subdirectories."""
    with (
        patch.object(sys, "argv", ["fmu", "init"]),
        pytest.raises(SystemExit, match="1"),
    ):
        main()

    captured = capsys.readouterr()
    stderr = captured.err.replace("\n", " ")
    assert "does not appear to be an FMU project" in stderr
    assert "ert" in stderr


def test_init_checks_if_fmu_dir_passes(in_tmp_path: Path) -> None:
    """Tests that 'fmu init' checks if the directory has required subdirectories."""
    for dir_ in REQUIRED_FMU_PROJECT_SUBDIRS:
        (in_tmp_path / dir_).mkdir(parents=True, exist_ok=True)
    fmu_dir = in_tmp_path / ".fmu"
    assert fmu_dir.exists() is False
    with (
        patch.object(sys, "argv", ["fmu", "init"]),
        pytest.raises(SystemExit, match="0"),
    ):
        main()
    assert fmu_dir.exists() is True


def test_init_does_not_check_if_fmu_dir_is_forced(in_tmp_path: Path) -> None:
    """Tests that 'fmu init --force' doesn't check if the dir has required subdirs."""
    fmu_dir = in_tmp_path / ".fmu"
    assert fmu_dir.exists() is False
    with (
        patch.object(sys, "argv", ["fmu", "init", "--force"]),
        pytest.raises(SystemExit, match="0"),
    ):
        main()
    assert fmu_dir.exists() is True


def test_init_looks_for_global_config(in_fmu_project: Path) -> None:
    """Tests that 'fmu init' checks if the directory has required subdirectories."""
    with (
        patch.object(sys, "argv", ["fmu", "init"]),
        patch(
            "fmu_settings_cli.init.main.find_global_config"
        ) as mock_find_global_config,
        pytest.raises(SystemExit, match="0"),
    ):
        main()
        mock_find_global_config.assert_called_once_with(in_fmu_project)


def test_init_adds_global_variables_without_masterdata(
    in_fmu_project: Path, global_variables_without_masterdata: dict[str, Any]
) -> None:
    """Tests that 'fmu init' fails creating a .fmu if the config has no masterdata."""
    tmp_path = in_fmu_project
    fmuconfig_out = tmp_path / "fmuconfig/output"
    fmuconfig_out.mkdir(parents=True, exist_ok=True)

    (fmuconfig_out / "global_variables.yml").write_text(
        yaml.safe_dump(global_variables_without_masterdata)
    )

    with (
        patch.object(sys, "argv", ["fmu", "init"]),
        pytest.raises(SystemExit, match="1"),
    ):
        main()

    with pytest.raises(FileNotFoundError):
        find_nearest_fmu_directory()


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

    with (
        patch.object(sys, "argv", ["fmu", "init"]),
        pytest.raises(SystemExit, match="0"),
    ):
        main()
    fmu_dir = find_nearest_fmu_directory()
    fmu_dir_cfg = fmu_dir.config.load()
    assert fmu_dir_cfg.masterdata == valid_global_cfg.masterdata
    assert fmu_dir_cfg.access is not None
    assert fmu_dir_cfg.model is not None


def test_init_skips_adding_global_variables_with_masterdata(
    in_fmu_project: Path,
    generate_strict_valid_globalconfiguration: Callable[[], GlobalConfiguration],
) -> None:
    """Tests that 'fmu init' skips adding masterdata with skip flag."""
    tmp_path = in_fmu_project

    valid_global_cfg = generate_strict_valid_globalconfiguration()

    fmuconfig_out = tmp_path / "fmuconfig/output"
    fmuconfig_out.mkdir(parents=True, exist_ok=True)

    (fmuconfig_out / "global_variables.yml").write_text(
        yaml.dump(valid_global_cfg.model_dump(mode="json", by_alias=True))
    )

    with (
        patch.object(sys, "argv", ["fmu", "init", "--skip-config-import"]),
        pytest.raises(SystemExit, match="0"),
    ):
        main()

    fmu_dir = find_nearest_fmu_directory()
    fmu_dir_cfg = fmu_dir.config.load()
    assert fmu_dir_cfg.masterdata is None
    assert fmu_dir_cfg.access is None
    assert fmu_dir_cfg.model is None


def test_init_raises_when_import_drogon_masterdata(
    in_fmu_project: Path,
    global_variables_with_masterdata: dict[str, Any],
    capsys: CaptureFixture[str],
) -> None:
    """Tests that 'fmu init' fails when importing Drogon masterdata."""
    tmp_path = in_fmu_project

    fmuconfig_out = tmp_path / "fmuconfig/output"
    fmuconfig_out.mkdir(parents=True, exist_ok=True)

    (fmuconfig_out / "global_variables.yml").write_text(
        yaml.dump(global_variables_with_masterdata)
    )

    with (
        patch.object(sys, "argv", ["fmu", "init"]),
        pytest.raises(SystemExit, match="1"),
    ):
        main()

    captured = capsys.readouterr()
    stderr = captured.err.replace("\n", " ").replace("  ", " ")
    assert "Reason: Invalid name in 'model': Drogon" in stderr


def test_init_skips_raising_when_import_drogon_masterdata_with_skip(
    in_fmu_project: Path, global_variables_with_masterdata: dict[str, Any]
) -> None:
    """Tests that 'fmu init' skips raising on Drogon masterdata with skip flag."""
    tmp_path = in_fmu_project

    fmuconfig_out = tmp_path / "fmuconfig/output"
    fmuconfig_out.mkdir(parents=True, exist_ok=True)

    (fmuconfig_out / "global_variables.yml").write_text(
        yaml.dump(global_variables_with_masterdata)
    )

    # Does not raise
    with (
        patch.object(sys, "argv", ["fmu", "init", "--skip-config-import"]),
        pytest.raises(SystemExit, match="0"),
    ):
        main()
    fmu_dir = find_nearest_fmu_directory()
    fmu_dir_cfg = fmu_dir.config.load()
    assert fmu_dir_cfg.masterdata is None
    assert fmu_dir_cfg.access is None
    assert fmu_dir_cfg.model is None
