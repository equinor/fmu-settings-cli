"""Tests for the settings application server."""

from typing import Any
from unittest.mock import MagicMock, call, patch

from pytest import CaptureFixture

from fmu_settings_cli.settings._utils import generate_auth_token
from fmu_settings_cli.settings.main import init_worker, start_app


def _executor_with_future(mock_executor: MagicMock, future: MagicMock) -> MagicMock:
    """Configure a mocked process executor and return its instance."""
    executor = MagicMock()
    executor._processes = {}
    executor.submit.return_value = future
    mock_executor.return_value.__enter__.return_value = executor
    return executor


def test_start_app_serves_gui_and_opens_browser_after_health_check(
    default_settings_args: dict[str, Any],
) -> None:
    """The one server gets the GUI directory and opens only after HTTP 200."""
    token = generate_auth_token()
    future = MagicMock()
    future.result.side_effect = [TimeoutError, None]

    with (
        patch("fmu_settings_cli.settings.main.ProcessPoolExecutor") as mock_executor,
        patch("fmu_settings_cli.settings.main.start_api_server") as mock_start_server,
        patch("fmu_settings_cli.settings.main.urllib.request.urlopen") as mock_urlopen,
        patch("fmu_settings_cli.settings.main.webbrowser.open") as mock_browser_open,
    ):
        executor = _executor_with_future(mock_executor, future)
        health_response = MagicMock()
        health_response.__enter__.return_value.status = 200
        mock_urlopen.return_value = health_response

        ordered_calls = MagicMock()
        ordered_calls.attach_mock(mock_urlopen, "health")
        ordered_calls.attach_mock(mock_browser_open, "browser")

        start_app(token, **default_settings_args)

    port = default_settings_args["port"]
    host = default_settings_args["host"]
    health_url = f"http://{host}:{port}/health"
    browser_url = f"http://{host}:{port}/#token={token}"

    mock_executor.assert_called_once_with(max_workers=1, initializer=init_worker)
    executor.submit.assert_called_once_with(
        mock_start_server,
        token,
        host=host,
        port=port,
        frontend_host=host,
        frontend_port=port,
        reload=False,
        log_level=default_settings_args["log_level"],
        frontend_directory=default_settings_args["frontend_directory"],
    )
    mock_urlopen.assert_called_once_with(health_url, timeout=0.5)
    mock_browser_open.assert_called_once_with(browser_url)
    assert ordered_calls.mock_calls.index(
        call.health(health_url, timeout=0.5)
    ) < ordered_calls.mock_calls.index(call.browser(browser_url))


def test_start_app_stops_when_health_check_times_out(
    default_settings_args: dict[str, Any], capsys: CaptureFixture[str]
) -> None:
    """A failed health check keeps the browser closed and stops the server."""
    future = MagicMock()
    future.result.side_effect = TimeoutError

    with (
        patch("fmu_settings_cli.settings.main.ProcessPoolExecutor") as mock_executor,
        patch(
            "fmu_settings_cli.settings.main.urllib.request.urlopen",
            side_effect=OSError,
        ) as mock_urlopen,
        patch("fmu_settings_cli.settings.main.time.monotonic", side_effect=[0, 6]),
        patch("fmu_settings_cli.settings.main.webbrowser.open") as mock_browser_open,
    ):
        executor = _executor_with_future(mock_executor, future)
        start_app(generate_auth_token(), **default_settings_args)

    mock_urlopen.assert_called_once()
    mock_browser_open.assert_not_called()
    future.cancel.assert_called_once()
    executor.shutdown.assert_called_once_with(wait=False, cancel_futures=True)
    stderr = " ".join(capsys.readouterr().err.split())
    assert "Application did not become ready within 5 seconds." in stderr
    assert "Shutting down FMU Settings." in stderr
    assert "Health check failed." in stderr


def test_start_app_does_not_open_browser_for_unhealthy_response(
    default_settings_args: dict[str, Any], capsys: CaptureFixture[str]
) -> None:
    """A non-200 health response does not open the browser."""
    future = MagicMock()
    future.result.side_effect = TimeoutError

    with (
        patch("fmu_settings_cli.settings.main.ProcessPoolExecutor") as mock_executor,
        patch("fmu_settings_cli.settings.main.urllib.request.urlopen") as mock_urlopen,
        patch("fmu_settings_cli.settings.main.time.monotonic", side_effect=[0, 6]),
        patch("fmu_settings_cli.settings.main.webbrowser.open") as mock_browser_open,
    ):
        _executor_with_future(mock_executor, future)
        health_response = MagicMock()
        health_response.__enter__.return_value.status = 503
        mock_urlopen.return_value = health_response
        start_app(generate_auth_token(), **default_settings_args)

    mock_browser_open.assert_not_called()
    assert (
        "Application did not become ready within 5 seconds." in capsys.readouterr().err
    )


def test_start_app_handles_keyboard_interrupt(
    default_settings_args: dict[str, Any], capsys: CaptureFixture[str]
) -> None:
    """CTRL+C stops the child server and reports the shutdown."""
    future = MagicMock()
    future.result.side_effect = KeyboardInterrupt

    with patch("fmu_settings_cli.settings.main.ProcessPoolExecutor") as mock_executor:
        executor = _executor_with_future(mock_executor, future)
        process = MagicMock()
        executor._processes = {1: process}
        start_app(generate_auth_token(), **default_settings_args)

    assert "Shutting down FMU Settings ..." in capsys.readouterr().out
    process.terminate.assert_called_once()


def test_start_app_reports_system_exit(
    default_settings_args: dict[str, Any], capsys: CaptureFixture[str]
) -> None:
    """A fatal Uvicorn exit includes the application port."""
    future = MagicMock()
    future.result.side_effect = SystemExit(1)

    with patch("fmu_settings_cli.settings.main.ProcessPoolExecutor") as mock_executor:
        _executor_with_future(mock_executor, future)
        start_app(generate_auth_token(), **default_settings_args)

    stderr = capsys.readouterr().err.replace("\n", " ")
    assert "Application server exited with exit code 1." in stderr
    assert f"port {default_settings_args['port']}" in stderr


def test_start_app_reports_unexpected_exit(
    default_settings_args: dict[str, Any], capsys: CaptureFixture[str]
) -> None:
    """A server that returns is reported as an unexpected exit."""
    future = MagicMock()
    future.result.return_value = None

    with patch("fmu_settings_cli.settings.main.ProcessPoolExecutor") as mock_executor:
        _executor_with_future(mock_executor, future)
        start_app(generate_auth_token(), **default_settings_args)

    assert "Application server unexpectedly exited." in capsys.readouterr().err


def test_start_app_reports_exception(
    default_settings_args: dict[str, Any], capsys: CaptureFixture[str]
) -> None:
    """An application server exception is reported."""
    future = MagicMock()
    future.result.side_effect = OSError("foo")

    with patch("fmu_settings_cli.settings.main.ProcessPoolExecutor") as mock_executor:
        _executor_with_future(mock_executor, future)
        start_app(generate_auth_token(), **default_settings_args)

    assert "Application server failed with: foo" in capsys.readouterr().err
