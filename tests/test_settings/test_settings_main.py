"""Tests for the settings sub-command module."""

from collections.abc import Callable
from time import sleep
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from pytest import CaptureFixture

from fmu_settings_cli.settings._utils import generate_auth_token
from fmu_settings_cli.settings.constants import API_PORT, GUI_PORT
from fmu_settings_cli.settings.main import (
    init_worker,
    start_api_and_gui,
)


def test_start_api_and_gui_processes(default_settings_args: Any) -> None:
    """Tests that all processes are submitted to the executor with expected args."""
    token = generate_auth_token()

    with (
        patch("fmu_settings_cli.settings.main.ProcessPoolExecutor") as mock_executor,
        patch("fmu_settings_cli.settings.main.as_completed") as mock_as_completed,
        patch(
            "fmu_settings_cli.settings.main.start_api_server"
        ) as mock_start_api_server,
        patch(
            "fmu_settings_cli.settings.main.start_gui_server"
        ) as mock_start_gui_server,
        patch("fmu_settings_cli.settings.main.webbrowser.open") as mock_webbrowser_open,
    ):
        mock_executor_instance = MagicMock()
        # Patch over the ProcessPoolExecutor. This requires that objects submitted
        # to it are pickle-able, and mock objects _are not_. So extra mocking is
        # required.
        mock_executor.return_value.__enter__.return_value = mock_executor_instance

        mock_api_future = MagicMock()
        mock_gui_future = MagicMock()
        mock_browser_future = MagicMock()

        mock_executor_instance.submit.side_effect = [
            mock_api_future,
            mock_gui_future,
            mock_browser_future,
        ]

        mock_as_completed.return_value = iter([mock_api_future])

        # Whew. Start it up then do assertions.
        start_api_and_gui(token, *default_settings_args.values())

        mock_executor.assert_called_once_with(max_workers=3, initializer=init_worker)

        mock_executor_instance.submit.assert_any_call(
            mock_start_api_server,
            token,
            host=default_settings_args["host"],
            port=default_settings_args["api_port"],
            frontend_host=default_settings_args["host"],
            frontend_port=default_settings_args["gui_port"],
            reload=default_settings_args["reload"],
            log_level=default_settings_args["log_level"],
        )
        mock_executor_instance.submit.assert_any_call(
            mock_start_gui_server,
            token,
            host=default_settings_args["host"],
            port=default_settings_args["gui_port"],
            log_level=default_settings_args["log_level"],
        )
        mock_executor_instance.submit.assert_any_call(
            mock_webbrowser_open,
            f"http://{default_settings_args['host']}:{default_settings_args['gui_port']}/#token={token}",
        )

        mock_browser_future.result.assert_called_once()

        # Check this is called, but mostly because it blocks if not mocked
        mock_as_completed.assert_called_once()


def test_keyboard_interrupt_in_process_executor(
    default_settings_args: dict[str, Any], capsys: CaptureFixture[str]
) -> None:
    """Tests that a KeyboardInterrupt issue sthe correct message."""
    token = generate_auth_token()
    with (
        patch("fmu_settings_cli.settings.main.ProcessPoolExecutor") as mock_executor,
        patch(
            "fmu_settings_cli.settings.main.start_api_server"
        ) as mock_start_api_server,
        patch(
            "fmu_settings_cli.settings.main.start_gui_server"
        ) as mock_start_gui_server,
        patch("fmu_settings_cli.settings.main.webbrowser.open") as mock_webbrowser_open,
    ):
        mock_start_api_server.side_effect = lambda *args, **kwargs: None
        mock_start_gui_server.side_effect = lambda *args, **kwargs: None
        mock_webbrowser_open.return_value = True

        mock_executor_instance = MagicMock()
        mock_executor.return_value.__enter__.return_value = mock_executor_instance

        mock_api_future = MagicMock()
        mock_gui_future = MagicMock()
        mock_browser_future = MagicMock()
        mock_browser_future.result.side_effect = KeyboardInterrupt()

        mock_executor_instance.submit.side_effect = [
            mock_api_future,
            mock_gui_future,
            mock_browser_future,
        ]

        start_api_and_gui(token, *default_settings_args.values())

    captured = capsys.readouterr()
    stdout = captured.out.replace("\n", " ").replace("  ", " ")
    assert "Shutting down FMU Settings ..." in stdout


def _bad_exit_early(*args: Any, **kwargs: Any) -> None:
    """Used to test server failures.

    These must be present outside of the test so that they can be pickled and sent to
    child processes by the process executor.
    """
    sleep(0.1)
    # This will cause this process to be first (next()) in the as_completed queue.
    raise SystemExit(1)


def _wait(*args: Any, **kwargs: Any) -> None:
    """Used to test server failures."""
    sleep(0.2)


def _return_true(*args: Any, **kwargs: Any) -> bool:
    """Used to test server failures."""
    return True


@pytest.mark.parametrize(
    "failed_service, api_fn, gui_fn",
    [("GUI", _wait, _bad_exit_early), ("API", _bad_exit_early, _wait)],
)
def test_monitor_api_or_gui_server_system_exits(
    default_settings_args: dict[str, Any],
    capsys: CaptureFixture[str],
    failed_service: str,
    gui_fn: Callable[[Any], None],
    api_fn: Callable[[Any], None],
) -> None:
    """Tests that monitoring catches when the GUI/API server fails with SytemExit."""
    token = generate_auth_token()

    required_port = API_PORT if failed_service == "API" else GUI_PORT
    # These must be wrapped in lambdas for pickling.
    with (
        patch(
            "fmu_settings_cli.settings.main.start_api_server",
            new_callable=lambda *args, **kwargs: api_fn,
        ),
        patch(
            "fmu_settings_cli.settings.main.start_gui_server",
            new_callable=lambda *args, **kwargs: gui_fn,
        ),
        patch(
            "fmu_settings_cli.settings.main.webbrowser.open",
            new_callable=lambda *args, **kwargs: _return_true,
        ),
    ):
        start_api_and_gui(token, *default_settings_args.values())

    captured = capsys.readouterr()
    stderr = captured.err.replace("\n", " ").replace("  ", " ")
    assert f"Error: {failed_service} exited with exit code 1." in stderr
    assert f"port {required_port}" in stderr


@pytest.mark.parametrize(
    "failed_service, api_fn, gui_fn",
    [("GUI", _wait, _return_true), ("API", _return_true, _wait)],
)
def test_monitor_api_or_gui_server_exits_unexpectedly(
    default_settings_args: dict[str, Any],
    capsys: CaptureFixture[str],
    failed_service: str,
    gui_fn: Callable[[Any], None],
    api_fn: Callable[[Any], None],
) -> None:
    """Tests that monitoring catches when the API server fails."""
    token = generate_auth_token()

    # These must be wrapped in lambdas for pickling.
    with (
        patch(
            "fmu_settings_cli.settings.main.start_api_server",
            new_callable=lambda *args, **kwargs: api_fn,
        ),
        patch(
            "fmu_settings_cli.settings.main.start_gui_server",
            new_callable=lambda *args, **kwargs: gui_fn,
        ),
        patch(
            "fmu_settings_cli.settings.main.webbrowser.open",
            new_callable=lambda *args, **kwargs: _return_true,
        ),
    ):
        start_api_and_gui(token, *default_settings_args.values())

    captured = capsys.readouterr()
    stderr = captured.err.replace("\n", " ").replace("  ", " ")
    assert f"Error: {failed_service} unexpectedly exited." in stderr


def _raises_exception(*args: Any, **kwargs: Any) -> None:
    """Kills a server start with an exception."""
    raise OSError("foo")


@pytest.mark.parametrize(
    "failed_service, api_fn, gui_fn",
    [("GUI", _wait, _raises_exception), ("API", _raises_exception, _wait)],
)
def test_monitor_api_or_gui_server_raises_exception(
    default_settings_args: dict[str, Any],
    capsys: CaptureFixture[str],
    failed_service: str,
    gui_fn: Callable[[Any], None],
    api_fn: Callable[[Any], None],
) -> None:
    """Tests that monitoring catches when the API server fails."""
    token = generate_auth_token()

    # These must be wrapped in lambdas for pickling.
    with (
        patch(
            "fmu_settings_cli.settings.main.start_api_server",
            new_callable=lambda *args, **kwargs: api_fn,
        ),
        patch(
            "fmu_settings_cli.settings.main.start_gui_server",
            new_callable=lambda *args, **kwargs: gui_fn,
        ),
        patch(
            "fmu_settings_cli.settings.main.webbrowser.open",
            new_callable=lambda *args, **kwargs: _return_true,
        ),
    ):
        start_api_and_gui(token, *default_settings_args.values())

    captured = capsys.readouterr()
    stderr = captured.err.replace("\n", " ")
    assert f"Error: {failed_service} failed with: foo" in stderr
