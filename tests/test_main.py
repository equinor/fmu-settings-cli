"""Tests 'fmu *' functionality."""

from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from fmu_settings_cli.__main__ import app

runner = CliRunner()


@pytest.mark.parametrize(
    "cmd",
    [
        ["init", "--help"],
        ["settings", "--help"],
        ["sync", "--help"],
    ],
)
def test_cmds_create_user_fmu_if_not_exist(in_tmp_path: Path, cmd: list[str]) -> None:
    """Tests that all 'fmu *' commands create a user .fmu/ dir."""
    home = in_tmp_path / "user"
    home.mkdir()

    with patch("pathlib.Path.home", return_value=home):
        result = runner.invoke(app, cmd)

    assert result.exit_code == 0
    assert (home / ".fmu").exists()
