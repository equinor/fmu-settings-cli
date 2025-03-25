"""Tests for the __main__ module."""

import argparse
import sys
from unittest.mock import MagicMock, patch

from pytest import CaptureFixture

from fmu_settings_cli.__main__ import (
    _parse_args,
    generate_auth_token,
    init_worker,
    main,
    start_api_and_gui,
)


def test_parse_args_no_input() -> None:
    """Tests that parse_args falls back to sys.argv."""
    expected = 9999
    with patch.object(sys, "argv", ["fmu-settings", "api", "--port", str(expected)]):
        args = _parse_args()
    assert args.port == expected


def test_main_invocation_with_no_options() -> None:
    """Tests that fmu-settings calls 'start_api_and_gui'."""
    with patch("fmu_settings_cli.__main__.start_api_and_gui") as mock_start_api_and_gui:
        main([])
        mock_start_api_and_gui.assert_called_once()


def test_main_invocation_with_api_subcommand() -> None:
    """Tests that fmu-settings calls 'start_api_and_gui'."""
    with patch("fmu_settings_cli.__main__.start_api_server") as mock_start_api_server:
        main(["api"])
        mock_start_api_server.assert_called_once()


def test_main_invocation_with_gui_subcommand() -> None:
    """Tests that fmu-settings calls 'start_api_and_gui'."""
    with patch("fmu_settings_cli.__main__.start_gui_server") as mock_start_gui_server:
        main(["gui"])
        mock_start_gui_server.assert_called_once()


def test_generate_auth_token() -> None:
    """Tests generating an authentication token."""
    assert len(generate_auth_token()) == 64  # noqa
    assert generate_auth_token() != generate_auth_token() != generate_auth_token()


def test_start_api_and_gui_processes(default_args: argparse.Namespace) -> None:
    """Tests that all processes are submitted to the executor with expected args."""
    token = generate_auth_token()

    with (
        patch("fmu_settings_cli.__main__.ProcessPoolExecutor") as mock_executor,
        patch("fmu_settings_cli.__main__.start_api_server") as mock_start_api_server,
        patch("fmu_settings_cli.__main__.start_gui_server") as mock_start_gui_server,
        patch("fmu_settings_cli.__main__.webbrowser.open") as mock_webbrowser_open,
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

        # Whew. Start it up then do assertions.
        start_api_and_gui(token, default_args)

        mock_executor.assert_called_once_with(max_workers=3, initializer=init_worker)

        mock_executor_instance.submit.assert_any_call(
            mock_start_api_server,
            token,
            host=default_args.host,
            port=default_args.api_port,
            frontend_host=default_args.host,
            frontend_port=default_args.gui_port,
        )
        mock_executor_instance.submit.assert_any_call(
            mock_start_gui_server,
            token,
            host=default_args.host,
            port=default_args.gui_port,
        )
        mock_executor_instance.submit.assert_any_call(
            mock_webbrowser_open,
            f"http://localhost:{default_args.gui_port}/#token={token}",
        )

        mock_browser_future.result.assert_called_once()


def test_keyboard_interrupt_in_process_executor(
    default_args: argparse.Namespace, capsys: CaptureFixture[str]
) -> None:
    """Tests that a KeyboardInterrupt issue sthe correct message."""
    token = generate_auth_token()
    with (
        patch("fmu_settings_cli.__main__.ProcessPoolExecutor") as mock_executor,
        patch("fmu_settings_cli.__main__.start_api_server") as mock_start_api_server,
        patch("fmu_settings_cli.__main__.start_gui_server") as mock_start_gui_server,
        patch("fmu_settings_cli.__main__.webbrowser.open") as mock_webbrowser_open,
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

        start_api_and_gui(token, default_args)
        captured = capsys.readouterr()

        assert "\nShutting down FMU Settings..." in captured.out
