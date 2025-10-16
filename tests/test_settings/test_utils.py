"""Tests for the simple utility functions in _utils.py."""

import subprocess
from unittest.mock import MagicMock, patch

import pytest
import typer
from pytest import CaptureFixture

from fmu_settings_cli.settings._utils import (
    create_authorized_url,
    ensure_port,
    generate_auth_token,
    get_process_on_port,
)
from fmu_settings_cli.settings.constants import INVALID_PID


def test_generate_auth_token() -> None:
    """Tests generating an authentication token."""
    assert len(generate_auth_token()) == 64  # noqa
    assert generate_auth_token() != generate_auth_token() != generate_auth_token()


def test_create_authorized_url() -> None:
    """Tests creating an authorized url."""
    token = generate_auth_token()
    assert (
        create_authorized_url(token, "localhost", 1234)
        == f"http://localhost:1234/#token={token}"
    )


@patch("subprocess.run")
def test_get_process_on_port_success(mock_run: MagicMock) -> None:
    """Tests that the correct process on a port is found."""
    mock_lsof = MagicMock()
    mock_lsof.stdout = "1234\n"
    mock_lsof.returncode = 0

    mock_ps = MagicMock()
    mock_ps.stdout = "python3\n"
    mock_ps.returncode = 0

    mock_run.side_effect = [mock_lsof, mock_ps]

    result = get_process_on_port(8000)

    assert result == (1234, "python3")

    mock_run.assert_any_call(
        ["lsof", "-i", ":8000", "-t"],
        capture_output=True,
        text=True,
        check=True,
    )
    mock_run.assert_any_call(
        ["ps", "-p", "1234", "-o", "comm="],
        capture_output=True,
        text=True,
        check=True,
    )


@patch("subprocess.run")
def test_get_process_on_port_no_process(mock_run: MagicMock) -> None:
    """Tests that the correct result is returned if no process is found."""
    mock_lsof = MagicMock()
    mock_lsof.stdout = "\n"
    mock_lsof.returncode = 0

    mock_run.return_value = mock_lsof

    result = get_process_on_port(9999)
    assert result == (INVALID_PID, "Error")

    mock_run.assert_any_call(
        ["lsof", "-i", ":9999", "-t"],
        capture_output=True,
        text=True,
        check=True,
    )


@patch("subprocess.run")
def test_get_process_on_port_subprocess_fails(mock_run: MagicMock) -> None:
    """Tests that the correct result is returned if no process is found."""
    mock_lsof = MagicMock()
    mock_lsof.stdout = "\n"
    mock_lsof.returncode = 1

    mock_run.side_effect = subprocess.CalledProcessError(1, "lsof")

    result = get_process_on_port(9999)
    assert result == (INVALID_PID, "Error")


@patch("fmu_settings_cli.settings._utils.get_process_on_port")
def test_ensure_port_does_nothing_if_invalid_pid(mock_get_process: MagicMock) -> None:
    """Tests the valid, success case of ensure_port()."""
    mock_get_process.return_value = (INVALID_PID, "Error")
    # Does not raise/fail
    ensure_port(8000)


@patch("fmu_settings_cli.settings._utils.get_process_on_port")
def test_ensure_port_sys_exits_if_port_in_use(
    mock_get_process: MagicMock, capsys: CaptureFixture[str]
) -> None:
    """Tests the valid, success case of ensure_port()."""
    mock_get_process.return_value = (1234, "python3")
    with pytest.raises(typer.Abort):
        ensure_port(8000)
    captured = capsys.readouterr()
    assert "port 8000" in captured.err
    assert "PID: 1234" in captured.err
    assert "command: python3" in captured.err
