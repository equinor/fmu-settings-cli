"""Tests for restarting the application on an occupied port."""

import signal
from unittest.mock import MagicMock, call, patch

import pytest
import typer
from pytest import CaptureFixture
from typer.testing import CliRunner

from fmu_settings_cli.settings.constants import INVALID_PID
from fmu_settings_cli.settings.restart import (
    confirm_restart,
    stop_process,
)


@pytest.mark.parametrize(
    ("answer", "restart"),
    [
        ("\n", False),
        ("n\n", False),
        ("N\n", False),
        ("y\n", True),
        ("yes\n", True),
        ("invalid\n\n", False),
        ("", False),
    ],
)
def test_confirm_restart_requires_explicit_yes(answer: str, restart: bool) -> None:
    """Tests that restart requires an explicit Yes and Enter keeps the current app."""
    app = typer.Typer()

    @app.command()
    def confirm() -> None:
        typer.echo(f"restart={confirm_restart()}")

    result = CliRunner().invoke(app, input=answer)
    assert result.exit_code == 0
    assert f"restart={restart}" in result.stdout
    assert "Press Enter or type n to keep the current app running." in result.stdout
    assert "Restart FMU Settings? [y/N]:" in result.stdout


def test_confirm_restart_returns_false_when_aborted() -> None:
    """Tests that an interrupted confirmation leaves the current app running."""
    with patch(
        "fmu_settings_cli.settings.restart.typer.confirm", side_effect=typer.Abort
    ):
        assert confirm_restart() is False


def test_stop_process_stops_listener_found_after_confirmation() -> None:
    """Tests that the current listener is stopped and awaited before a port check."""
    calls = MagicMock()
    with (
        patch(
            "fmu_settings_cli.settings.restart.os.kill",
            side_effect=[None, None, ProcessLookupError],
        ) as kill,
        patch("fmu_settings_cli.settings.restart.time.sleep") as sleep,
        patch(
            "fmu_settings_cli.settings.restart.get_process_on_port",
            side_effect=[(5678, "python"), (INVALID_PID, "Error")],
        ) as listener,
    ):
        calls.attach_mock(kill, "signal")
        calls.attach_mock(listener, "listener")
        stop_process(8000)
    assert calls.mock_calls == [
        call.listener(8000),
        call.signal(5678, signal.SIGTERM),
        call.signal(5678, 0),
        call.signal(5678, 0),
        call.listener(8000),
    ]
    sleep.assert_called_once()


def test_stop_process_sends_no_signal_when_listener_is_gone() -> None:
    """Tests that no signal is sent when the port is free after confirmation."""
    with (
        patch("fmu_settings_cli.settings.restart.os.kill") as kill,
        patch(
            "fmu_settings_cli.settings.restart.get_process_on_port",
            return_value=(INVALID_PID, "Error"),
        ) as listener,
    ):
        stop_process(8000)
    listener.assert_called_once_with(8000)
    kill.assert_not_called()


def test_stop_process_aborts_on_shutdown_timeout(capsys: CaptureFixture[str]) -> None:
    """Tests that a shutdown timeout aborts without sending SIGKILL."""
    with (
        patch("fmu_settings_cli.settings.restart.os.kill") as kill,
        patch("fmu_settings_cli.settings.restart.time.monotonic", side_effect=[0, 31]),
        patch(
            "fmu_settings_cli.settings.restart.get_process_on_port",
            return_value=(1234, "python"),
        ) as listener,
        pytest.raises(typer.Abort),
    ):
        stop_process(8000)
    listener.assert_called_once_with(8000)
    assert [call.args for call in kill.call_args_list] == [
        (1234, signal.SIGTERM),
        (1234, 0),
    ]
    assert "has not finished shutting down" in capsys.readouterr().err


def test_stop_process_handles_listener_exiting_before_signal() -> None:
    """Tests that a listener exiting before SIGTERM does not prevent restart."""
    with (
        patch(
            "fmu_settings_cli.settings.restart.os.kill", side_effect=ProcessLookupError
        ) as kill,
        patch(
            "fmu_settings_cli.settings.restart.get_process_on_port",
            side_effect=[(1234, "python"), (INVALID_PID, "Error")],
        ),
    ):
        stop_process(8000)
    assert [call.args for call in kill.call_args_list] == [
        (1234, signal.SIGTERM),
        (1234, 0),
    ]


@pytest.mark.parametrize("failure", [PermissionError, OSError])
@pytest.mark.parametrize("during_wait", [False, True])
def test_stop_process_aborts_when_signal_fails(
    failure: type[OSError], during_wait: bool, capsys: CaptureFixture[str]
) -> None:
    """Tests that signal or process-check failures abort without a second port check."""
    effects = [None, failure()] if during_wait else [failure()]
    with (
        patch("fmu_settings_cli.settings.restart.os.kill", side_effect=effects),
        patch(
            "fmu_settings_cli.settings.restart.get_process_on_port",
            return_value=(1234, "python"),
        ) as listener,
        pytest.raises(typer.Abort),
    ):
        stop_process(8000)
    listener.assert_called_once_with(8000)
    assert "Could not restart FMU Settings." in capsys.readouterr().err


def test_stop_process_aborts_if_another_listener_takes_port() -> None:
    """Tests that a new listener prevents restart and receives no shutdown signal."""
    with (
        patch(
            "fmu_settings_cli.settings.restart.os.kill",
            side_effect=[None, ProcessLookupError],
        ) as kill,
        patch(
            "fmu_settings_cli.settings.restart.get_process_on_port",
            side_effect=[(1234, "python"), (5678, "other-server")],
        ),
        pytest.raises(typer.Abort),
    ):
        stop_process(8000)
    assert [call.args for call in kill.call_args_list] == [
        (1234, signal.SIGTERM),
        (1234, 0),
    ]


def test_stop_process_aborts_if_final_port_lookup_fails() -> None:
    """Tests that a failed port lookup after process exit aborts the restart."""
    failure = typer.Abort()
    with (
        patch(
            "fmu_settings_cli.settings.restart.os.kill",
            side_effect=[None, ProcessLookupError],
        ) as kill,
        patch(
            "fmu_settings_cli.settings.restart.get_process_on_port",
            side_effect=[(1234, "python"), failure],
        ) as listener,
        pytest.raises(typer.Abort) as aborted,
    ):
        stop_process(8000)
    assert aborted.value is failure
    assert listener.call_args_list == [call(8000), call(8000)]
    assert [call.args for call in kill.call_args_list] == [
        (1234, signal.SIGTERM),
        (1234, 0),
    ]
