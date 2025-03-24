"""Tests for the __main__ module."""

import sys
from unittest.mock import MagicMock, patch

from fmu_settings_cli.__main__ import (
    _parse_args,
    generate_auth_token,
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


def test_start_api_and_gui_threads() -> None:
    """Tests that all three threads are started."""
    token = generate_auth_token()
    args = MagicMock()
    with (
        patch("fmu_settings_cli.__main__.start_api_server") as mock_start_api_server,
        patch("fmu_settings_cli.__main__.start_gui_server") as mock_start_gui_server,
        patch("fmu_settings_cli.__main__.webbrowser.open") as mock_webbrowser_open,
    ):
        start_api_and_gui(token, args)
        mock_start_api_server.assert_called_once()
        mock_start_gui_server.assert_called_once()
        mock_webbrowser_open.assert_called_once()


def test_keyboard_interrupt_kills_threads() -> None:
    """Tests that all three threads are started and killed on a KeyboardInterrupt."""
    token = generate_auth_token()
    args = MagicMock()
    with (
        patch("fmu_settings_cli.__main__.start_api_server") as mock_start_api_server,
        patch("fmu_settings_cli.__main__.start_gui_server") as mock_start_gui_server,
        patch(
            "fmu_settings_cli.__main__.webbrowser.open", side_effect=KeyboardInterrupt
        ) as mock_webbrowser_open,
        patch("fmu_settings_cli.__main__.sys.exit") as mock_sys_exit,
    ):
        start_api_and_gui(token, args)
        mock_start_api_server.assert_called_once()
        mock_start_gui_server.assert_called_once()
        mock_webbrowser_open.assert_called_once()
        mock_sys_exit.assert_called_once()
