"""Tests for the 'fmu settings' commands."""

import sys
from collections.abc import Generator
from pathlib import Path
from types import ModuleType
from unittest.mock import MagicMock, call, patch

import pytest
import typer
from typer.testing import CliRunner

from fmu_settings_cli.__main__ import app
from fmu_settings_cli.settings.cli import _get_static_directory
from fmu_settings_cli.settings.constants import APP_PORT, HOST, NO_PROCESS_PID

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


def test_settings_cmd_with_help(mock_available_port: Generator[None]) -> None:
    """Tests that 'fmu settings' emits help information."""
    result = runner.invoke(app, ["settings", "--help"])

    assert result.exit_code == 0
    assert "Start the FMU Settings application" in result.stdout
    assert "Start the FMU Settings API only" in result.stdout
    assert "--port" in result.stdout
    assert "--api-port" not in result.stdout
    assert "--gui-port" not in result.stdout
    assert "--log-level" in result.stdout


def test_settings_cmd_with_no_options(mock_available_port: Generator[None]) -> None:
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
    mock_available_port: Generator[None],
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
    mock_available_port: Generator[None],
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
    mock_available_port: Generator[None],
) -> None:
    """Tests that the development GUI port must match the Azure registration."""
    result = runner.invoke(app, ["settings", "api", "--gui-port", "9999"])

    assert result.exit_code == 2
    assert (
        "Invalid value for '--gui-port': '9999' is not one of '5173', '3000', '8000'"
        in result.stderr
    )


def test_settings_api_cmd(mock_available_port: Generator[None]) -> None:
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


def test_settings_api_cmd_with_help(mock_available_port: Generator[None]) -> None:
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
    mock_available_port: Generator[None],
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
    mock_available_port: Generator[None],
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
    mock_available_port: Generator[None],
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
    mock_available_port: Generator[None],
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
        patch("fmu_settings_cli.settings.cli.ensure_fmu_settings"),
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
        patch("fmu_settings_cli.settings.cli.ensure_fmu_settings") as identify,
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
        calls.attach_mock(identify, "identify")
        calls.attach_mock(confirm, "confirm")
        calls.attach_mock(stop, "stop")
        calls.attach_mock(start, "start")
        result = runner.invoke(app, ["settings", *port_args])
    assert result.exit_code == 0
    lookup.assert_called_once_with(port)
    stop.assert_called_once_with(port, "localhost")
    assert start.call_args.kwargs["port"] == port
    identify.assert_called_once_with(port, "localhost")
    assert [call[0] for call in calls.mock_calls] == [
        "identify",
        "confirm",
        "stop",
        "start",
    ]


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
            return_value=(NO_PROCESS_PID, "Error"),
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
        patch("fmu_settings_cli.settings.cli.ensure_fmu_settings"),
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
        stop.assert_called_once_with(APP_PORT, "localhost")


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


def test_settings_does_not_offer_restart_for_unidentified_listener() -> None:
    """Tests that an unidentified listener prevents the prompt and startup."""
    with (
        patch(
            "fmu_settings_cli.settings.cli.get_process_on_port",
            return_value=(1234, "python"),
        ),
        patch(
            "fmu_settings_cli.settings.cli.ensure_fmu_settings",
            side_effect=typer.Abort,
        ) as identify,
        patch("fmu_settings_cli.settings.cli.confirm_restart") as confirm,
        patch("fmu_settings_cli.settings.cli.stop_process") as stop,
        patch("fmu_settings_cli.settings.cli.start_app") as start,
    ):
        result = runner.invoke(
            app, ["settings", "--host", "127.0.0.1", "--port", "3000"]
        )
    assert result.exit_code == 1
    identify.assert_called_once_with(3000, "127.0.0.1")
    confirm.assert_not_called()
    stop.assert_not_called()
    start.assert_not_called()


def test_settings_rechecks_identity_after_confirmation() -> None:
    """Tests that a changed application after confirmation receives no signal."""
    initial_response = MagicMock()
    initial_response.status = 200
    initial_response.read.return_value = b'{"application": "fmu-settings"}'
    replacement_response = MagicMock()
    replacement_response.status = 200
    replacement_response.read.return_value = b'{"application": "other"}'
    with (
        patch(
            "fmu_settings_cli.settings.cli.get_process_on_port",
            return_value=(1234, "python"),
        ),
        patch(
            "fmu_settings_cli.settings.restart.get_process_on_port",
            return_value=(5678, "other"),
        ),
        patch("fmu_settings_cli.settings.restart.urllib.request.urlopen") as urlopen,
        patch("fmu_settings_cli.settings.restart.os.kill") as kill,
        patch("fmu_settings_cli.settings.cli.start_app") as start,
    ):
        urlopen.return_value.__enter__.side_effect = [
            initial_response,
            replacement_response,
        ]
        result = runner.invoke(app, ["settings"], input="y\n")
    assert result.exit_code == 1
    assert "Restart FMU Settings?" in result.stdout
    assert urlopen.call_args_list == [
        call("http://localhost:8000/health", timeout=2),
        call("http://localhost:8000/health", timeout=2),
    ]
    kill.assert_not_called()
    start.assert_not_called()
