"""Tests for the 'fmu settings' commands."""

from collections.abc import Generator
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from fmu_settings_cli.__main__ import app
from fmu_settings_cli.settings.constants import API_PORT, GUI_PORT, HOST

# ruff: noqa: PLR2004

runner = CliRunner()


def test_settings_cmd_with_help(patch_ensure_port: Generator[None]) -> None:
    """Tests that 'fmu settings' emits help information."""
    result = runner.invoke(app, ["settings", "--help"])

    assert result.exit_code == 0
    assert "Start the FMU Settings application" in result.stdout
    assert "Start the FMU Settings GUI only" in result.stdout
    assert "Start the FMU Settings API only" in result.stdout
    assert "--log-level" in result.stdout


def test_settings_cmd_with_no_options(patch_ensure_port: Generator[None]) -> None:
    """Tests that 'fmu settings' calls 'start_api_and_gui'."""
    with patch(
        "fmu_settings_cli.settings.cli.start_api_and_gui"
    ) as mock_start_api_and_gui:
        result = runner.invoke(app, ["settings"])
        mock_start_api_and_gui.assert_called_once()

    assert result.exit_code == 0


def test_settings_cmd_with_port_host_options(
    patch_ensure_port: Generator[None],
) -> None:
    """Tests that 'fmu settings' calls passes ports and host."""
    with patch(
        "fmu_settings_cli.settings.cli.start_api_and_gui"
    ) as mock_start_api_and_gui:
        result = runner.invoke(
            app,
            ["settings", "--gui-port", "3000", "--api-port", "5678", "--host", "foo"],
        )

        mock_start_api_and_gui.assert_called_once()
        args = mock_start_api_and_gui.call_args.args

        assert args[0]  # Token
        assert args[1] == 5678  # API
        assert args[2] == 3000  # GUI
        assert args[3] == "foo"
        assert args[4] is False  # reload

    assert result.exit_code == 0


def test_settings_cmd_with_reload(
    patch_ensure_port: Generator[None],
) -> None:
    """Tests that 'fmu settings' calls passes ports and host."""
    with patch(
        "fmu_settings_cli.settings.cli.start_api_and_gui"
    ) as mock_start_api_and_gui:
        result = runner.invoke(app, ["settings", "--reload"])

        mock_start_api_and_gui.assert_called_once()
        args = mock_start_api_and_gui.call_args.args

        assert args[0]  # Token
        assert args[1] == API_PORT
        assert args[2] == GUI_PORT
        assert args[3] == HOST
        assert args[4] is True

    assert result.exit_code == 0


@pytest.mark.parametrize(
    "cmd",
    [
        ["settings"],
        ["settings", "api"],
        ["settings", "gui"],
    ],
)
def test_settings_cmds_with_invalid_gui_port(
    cmd: list[str], patch_ensure_port: Generator[None]
) -> None:
    """Tests that 'fmu settings' calls passes ports and host."""
    with patch("fmu_settings_cli.settings.cli.start_api_and_gui"):
        result = runner.invoke(app, cmd + ["--gui-port", "9999"])

    assert result.exit_code == 2
    assert (
        "Invalid value for '--gui-port': '9999' is not one of '5173', '3000', '8000'"
        in result.stderr
    )


def test_settings_api_cmd(patch_ensure_port: Generator[None]) -> None:
    """Tests that 'fmu settings api' calls 'start_api_server'."""
    with patch(
        "fmu_settings_cli.settings.cli.start_api_server"
    ) as mock_start_api_server:
        result = runner.invoke(app, ["settings", "api"])
        mock_start_api_server.assert_called_once()

    assert result.exit_code == 0


def test_settings_api_cmd_with_help(patch_ensure_port: Generator[None]) -> None:
    """Tests that 'fmu settings' emits help information."""
    result = runner.invoke(app, ["settings", "api", "--help"])

    assert result.exit_code == 0
    assert "Start the FMU Settings API only" in result.stdout
    assert "--reload" in result.stdout
    assert "--print-token" in result.stdout
    assert "--print-url" in result.stdout
    assert "--log-level" in result.stdout


def test_settings_api_cmd_with_reload(
    patch_ensure_port: Generator[None],
) -> None:
    """Tests that 'fmu settings api --reload' sets reload to True."""
    with patch(
        "fmu_settings_cli.settings.cli.start_api_server"
    ) as mock_start_api_server:
        result = runner.invoke(app, ["settings", "api", "--reload"])

        mock_start_api_server.assert_called_once()
        args = mock_start_api_server.call_args.args
        kwargs = mock_start_api_server.call_args.kwargs

        assert args[0]  # Token
        assert kwargs["port"] == API_PORT
        assert kwargs["frontend_port"] == GUI_PORT
        assert kwargs["host"] == kwargs["frontend_host"] == HOST
        assert kwargs["reload"] is True

    assert result.exit_code == 0


def test_settings_api_cmd_with_print_token(
    patch_ensure_port: Generator[None],
) -> None:
    """Tests that 'fmu settings api --print-token' prints the token value."""
    token = "foo"
    with (
        patch("fmu_settings_cli.settings.cli.generate_auth_token", return_value=token),
        patch(
            "fmu_settings_cli.settings.cli.start_api_server"
        ) as mock_start_api_server,
    ):
        result = runner.invoke(app, ["settings", "api", "--print-token"])

        mock_start_api_server.assert_called_once()

    assert result.exit_code == 0
    assert f"API Token: {token}" in result.stdout


def test_settings_api_cmd_with_print_url(
    patch_ensure_port: Generator[None],
) -> None:
    """Tests that 'fmu settings api --print-url' prints the auth URL."""
    token = "foo"
    with (
        patch("fmu_settings_cli.settings.cli.generate_auth_token", return_value=token),
        patch(
            "fmu_settings_cli.settings.cli.start_api_server"
        ) as mock_start_api_server,
    ):
        result = runner.invoke(app, ["settings", "api", "--print-url"])

        mock_start_api_server.assert_called_once()

    assert result.exit_code == 0
    assert f"Authorized URL: http://localhost:8000/#token={token}" in result.stdout


def test_settings_gui_cmd(patch_ensure_port: Generator[None]) -> None:
    """Tests that 'fmu settings gui' calls 'start_gui_server'."""
    with patch(
        "fmu_settings_cli.settings.cli.start_gui_server"
    ) as mock_start_gui_server:
        result = runner.invoke(app, ["settings", "gui"])
        mock_start_gui_server.assert_called_once()

    assert result.exit_code == 0


def test_settings_gui_cmd_with_help(patch_ensure_port: Generator[None]) -> None:
    """Tests that 'fmu settings gui' emits help information."""
    result = runner.invoke(app, ["settings", "gui", "--help"])

    assert result.exit_code == 0
    assert "Start the FMU Settings GUI only" in result.stdout
    assert "--log-level" in result.stdout


def test_settings_gui_cmd_with_host_port(
    patch_ensure_port: Generator[None],
) -> None:
    """Tests that 'fmu settings gui --gui-port --host' passes to start gui func."""
    with patch(
        "fmu_settings_cli.settings.cli.start_gui_server"
    ) as mock_start_gui_server:
        result = runner.invoke(
            app, ["settings", "gui", "--gui-port", "3000", "--host", "foo"]
        )

        mock_start_gui_server.assert_called_once()
        args = mock_start_gui_server.call_args.args
        kwargs = mock_start_gui_server.call_args.kwargs

        assert args[0]  # Token
        assert kwargs["port"] == 3000
        assert kwargs["host"] == "foo"

    assert result.exit_code == 0
