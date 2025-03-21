"""Tests for gui_server.py."""

import socket
from unittest.mock import patch

from fmu.settings.cli.__main__ import generate_auth_token
from fmu.settings.cli.gui_server import start_gui_server


def test_start_gui_server() -> None:
    """Tests that start_api_server calls as expected."""
    token = generate_auth_token()
    with patch("fmu.settings.cli.gui_server.run_server") as mock_run_server:
        start_gui_server(token)
        mock_run_server.assert_called_once()


def test_start_api_server_fails() -> None:
    """Tests that start_api_server failing raises an exception."""
    token = generate_auth_token()
    with (
        patch(
            "fmu.settings.cli.gui_server.run_server", side_effect=socket.error
        ) as mock_run_server,
        patch("fmu.settings.cli.gui_server.sys.exit") as mock_sys_exit,
    ):
        start_gui_server(token)
        mock_run_server.assert_called_once()
        mock_sys_exit.assert_called_once()
