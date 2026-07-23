"""Tests for the 'fmu settings' commands."""

import sys
from collections.abc import Generator
from pathlib import Path
from types import ModuleType
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from fmu_settings_cli.__main__ import app
from fmu_settings_cli.settings.cli import _get_static_directory
from fmu_settings_cli.settings.constants import API_PORT, APP_PORT, HOST

# ruff: noqa: PLR2004

runner = CliRunner()


def test_get_static_directory() -> None:
    """The CLI gets the built frontend from the GUI package."""
    expected_directory = Path("/frontend")
    gui_package = ModuleType("fmu_settings_gui")
    mock_get_static_directory = MagicMock(return_value=expected_directory)
    gui_package.__dict__["get_static_directory"] = mock_get_static_directory

    with patch.dict(sys.modules, {"fmu_settings_gui": gui_package}):
        assert _get_static_directory() == expected_directory

    mock_get_static_directory.assert_called_once_with()


def test_settings_cmd_with_help(patch_ensure_port: Generator[None]) -> None:
    """Tests that 'fmu settings' emits help information."""
    result = runner.invoke(app, ["settings", "--help"])

    assert result.exit_code == 0
    assert "Start the FMU Settings application" in result.stdout
    assert "Start the FMU Settings API only" in result.stdout
    assert "--port" in result.stdout
    assert "--api-port" not in result.stdout
    assert "--gui-port" not in result.stdout
    assert "--log-level" in result.stdout


def test_settings_cmd_with_no_options(patch_ensure_port: Generator[None]) -> None:
    """Tests that 'fmu settings' starts the combined application."""
    frontend_directory = Path("/frontend")
    with (
        patch("fmu_settings_cli.settings.cli.start_app") as mock_start_app,
        patch(
            "fmu_settings_cli.settings.cli._get_static_directory",
            return_value=frontend_directory,
        ),
    ):
        result = runner.invoke(app, ["settings"])

    assert result.exit_code == 0
    mock_start_app.assert_called_once()
    assert mock_start_app.call_args.kwargs["port"] == APP_PORT
    assert mock_start_app.call_args.kwargs["frontend_directory"] == frontend_directory


def test_settings_cmd_with_port_host_options(
    patch_ensure_port: Generator[None],
) -> None:
    """Tests that 'fmu settings' passes the application port and host."""
    with (
        patch("fmu_settings_cli.settings.cli.start_app") as mock_start_app,
        patch(
            "fmu_settings_cli.settings.cli._get_static_directory",
            return_value=Path("/frontend"),
        ),
    ):
        result = runner.invoke(
            app,
            ["settings", "--port", "3000", "--host", "foo"],
        )

    assert result.exit_code == 0
    mock_start_app.assert_called_once()
    args = mock_start_app.call_args.args
    kwargs = mock_start_app.call_args.kwargs

    assert args[0]  # Token
    assert kwargs["port"] == 3000
    assert kwargs["host"] == "foo"


def test_settings_cmd_with_invalid_port(
    patch_ensure_port: Generator[None],
) -> None:
    """Tests that the application port must match the Azure registration."""
    with patch("fmu_settings_cli.settings.cli.start_app"):
        result = runner.invoke(app, ["settings", "--port", "9999"])

    assert result.exit_code == 2
    assert (
        "Invalid value for '--port': '9999' is not one of '5173', '3000', '8000'"
        in result.stderr
    )


def test_settings_api_cmd_with_invalid_gui_port(
    patch_ensure_port: Generator[None],
) -> None:
    """Tests that the development GUI port must match the Azure registration."""
    result = runner.invoke(app, ["settings", "api", "--gui-port", "9999"])

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
        assert kwargs["frontend_port"] == APP_PORT
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
