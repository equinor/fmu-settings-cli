"""Tests for the 'fmu settings' commands."""

import sys
from collections.abc import Generator
from pathlib import Path
from types import ModuleType
from unittest.mock import MagicMock, patch

import pytest
import typer
from typer.testing import CliRunner

from fmu_settings_cli.__main__ import app
from fmu_settings_cli.settings.cli import _get_static_directory
from fmu_settings_cli.settings.constants import APP_PORT, HOST, INVALID_PID

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
        patch("fmu_settings_cli.settings.cli.uuid4", return_value="run-123"),
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
    assert mock_start_app.call_args.kwargs["run_id"] == "run-123"
    assert mock_start_app.call_args.kwargs["environment"] == "production"


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
    assert mock_start_api_server.call_args.kwargs["enable_telemetry"] is False
    assert mock_start_api_server.call_args.kwargs["run_id"] is None
    assert mock_start_api_server.call_args.kwargs["environment"] == "development"


def test_settings_api_cmd_with_help(patch_ensure_port: Generator[None]) -> None:
    """Tests that 'fmu settings' emits help information."""
    result = runner.invoke(app, ["settings", "api", "--help"])

    assert result.exit_code == 0
    assert "Start the FMU Settings API only" in result.stdout
    assert "--reload" in result.stdout
    assert "--print-token" in result.stdout
    assert "--print-url" in result.stdout
    assert "--telemetry" in result.stdout
    assert "--api-port" not in result.stdout
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
        assert kwargs["port"] == APP_PORT
        assert kwargs["frontend_port"] == APP_PORT
        assert kwargs["host"] == kwargs["frontend_host"] == HOST
        assert kwargs["reload"] is True

    assert result.exit_code == 0


def test_settings_api_cmd_with_telemetry(
    patch_ensure_port: Generator[None],
) -> None:
    """The development command enables telemetry only when requested."""
    with (
        patch("fmu_settings_cli.settings.cli.uuid4", return_value="run-123"),
        patch(
            "fmu_settings_cli.settings.cli.start_api_server"
        ) as mock_start_api_server,
    ):
        result = runner.invoke(app, ["settings", "api", "--telemetry"])

    assert result.exit_code == 0
    assert mock_start_api_server.call_args.kwargs["enable_telemetry"] is True
    assert mock_start_api_server.call_args.kwargs["run_id"] == "run-123"
    assert mock_start_api_server.call_args.kwargs["environment"] == "development"


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


def test_settings_keeps_existing_app_when_restart_is_declined() -> None:
    """Tests that declining restart leaves the existing app running."""
    with (
        patch(
            "fmu_settings_cli.settings.cli.get_process_on_port",
            return_value=(1234, "python"),
        ),
        patch("fmu_settings_cli.settings.cli.confirm_restart", return_value=False),
        patch("fmu_settings_cli.settings.cli.stop_process") as stop,
        patch("fmu_settings_cli.settings.cli.start_app") as start,
        patch("fmu_settings_cli.settings.cli.generate_auth_token") as token,
        patch("fmu_settings_cli.settings.cli._get_static_directory") as assets,
    ):
        result = runner.invoke(app, ["settings"])
    assert result.exit_code == 0
    start.assert_not_called()
    token.assert_not_called()
    assets.assert_not_called()
    stop.assert_not_called()


@pytest.mark.parametrize(
    ("port_args", "port"), [([], APP_PORT), (["--port", "3000"], 3000)]
)
def test_settings_stops_existing_app_before_starting_replacement(
    port_args: list[str], port: int
) -> None:
    """Tests that after Yes, the app on the selected port stops before startup."""
    calls = MagicMock()
    with (
        patch(
            "fmu_settings_cli.settings.cli.get_process_on_port",
            return_value=(1234, "python"),
        ) as lookup,
        patch(
            "fmu_settings_cli.settings.cli.confirm_restart", return_value=True
        ) as confirm,
        patch("fmu_settings_cli.settings.cli.stop_process") as stop,
        patch("fmu_settings_cli.settings.cli.start_app") as start,
        patch(
            "fmu_settings_cli.settings.cli._get_static_directory",
            return_value=Path("/frontend"),
        ),
    ):
        calls.attach_mock(confirm, "confirm")
        calls.attach_mock(stop, "stop")
        calls.attach_mock(start, "start")
        result = runner.invoke(app, ["settings", *port_args])
    assert result.exit_code == 0
    lookup.assert_called_once_with(port)
    stop.assert_called_once_with(port)
    assert start.call_args.kwargs["port"] == port
    assert [call[0] for call in calls.mock_calls] == ["confirm", "stop", "start"]


@pytest.mark.parametrize(
    ("port_args", "port"), [([], APP_PORT), (["--port", "3000"], 3000)]
)
def test_settings_starts_without_confirmation_when_port_is_free(
    port_args: list[str], port: int
) -> None:
    """Tests that a free selected port permits startup without confirmation."""
    with (
        patch(
            "fmu_settings_cli.settings.cli.get_process_on_port",
            return_value=(INVALID_PID, "Error"),
        ) as lookup,
        patch("fmu_settings_cli.settings.cli.confirm_restart") as confirm,
        patch("fmu_settings_cli.settings.cli.stop_process") as stop,
        patch("fmu_settings_cli.settings.cli.start_app") as start,
        patch(
            "fmu_settings_cli.settings.cli._get_static_directory",
            return_value=Path("/frontend"),
        ),
    ):
        result = runner.invoke(app, ["settings", *port_args])
    assert result.exit_code == 0
    lookup.assert_called_once_with(port)
    confirm.assert_not_called()
    stop.assert_not_called()
    start.assert_called_once()
    assert start.call_args.kwargs["port"] == port


@pytest.mark.parametrize("failed_step", ["lookup", "shutdown"])
def test_settings_does_not_start_when_restart_preparation_fails(
    failed_step: str,
) -> None:
    """Tests that listener lookup or shutdown failure prevents replacement startup."""
    with (
        patch(
            "fmu_settings_cli.settings.cli.get_process_on_port",
            return_value=(1234, "python"),
            side_effect=typer.Abort if failed_step == "lookup" else None,
        ),
        patch(
            "fmu_settings_cli.settings.cli.confirm_restart", return_value=True
        ) as confirm,
        patch(
            "fmu_settings_cli.settings.cli.stop_process",
            side_effect=typer.Abort if failed_step == "shutdown" else None,
        ) as stop,
        patch("fmu_settings_cli.settings.cli.start_app") as start,
        patch("fmu_settings_cli.settings.cli.start_api_server") as api,
    ):
        result = runner.invoke(app, ["settings"])
    assert result.exit_code == 1
    start.assert_not_called()
    api.assert_not_called()
    if failed_step == "lookup":
        confirm.assert_not_called()
        stop.assert_not_called()
    else:
        confirm.assert_called_once_with()
        stop.assert_called_once_with(APP_PORT)


def test_settings_api_port_conflict_does_not_offer_restart() -> None:
    """Tests that API-only startup does not offer or perform a restart."""
    with (
        patch("fmu_settings_cli.settings.cli.ensure_port", side_effect=typer.Abort),
        patch("fmu_settings_cli.settings.cli.confirm_restart") as confirm,
        patch("fmu_settings_cli.settings.cli.stop_process") as stop,
        patch("fmu_settings_cli.settings.cli.start_api_server") as api,
    ):
        result = runner.invoke(app, ["settings", "api"])
    assert result.exit_code == 1
    confirm.assert_not_called()
    stop.assert_not_called()
    api.assert_not_called()
