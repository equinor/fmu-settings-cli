"""Tests for gui_server.py."""

from unittest.mock import patch

import pytest
from pytest import CaptureFixture

from fmu_settings_cli.settings._utils import generate_auth_token
from fmu_settings_cli.settings.gui_server import start_gui_server


def test_start_gui_server() -> None:
    """Tests that start_gui_server calls as expected."""
    token = generate_auth_token()
    with patch("fmu_settings_gui.run_server") as mock_run_server:
        start_gui_server(token)
        mock_run_server.assert_called_once()


def test_start_gui_server_fails() -> None:
    """Tests that start_gui_server failing raises an exception."""
    token = generate_auth_token()
    with (
        patch(
            "fmu_settings_gui.run_server", side_effect=OSError("fail")
        ) as mock_run_server,
        pytest.raises(RuntimeError, match="Could not start GUI server: fail"),
    ):
        start_gui_server(token)
        mock_run_server.assert_called_once()


def test_starting_gui_server_with_unknown_azure_port_exits(
    capsys: CaptureFixture[str],
) -> None:
    """Tests that starting the gui server with an unknown port exits.

    This is due to the gui server needing to use particular ports to authenticate with
    Azure/SSO.
    """
    token = generate_auth_token()
    bad_port = 1234
    with pytest.raises(ValueError, match=f"Port {bad_port} is not known"):
        start_gui_server(token, port=bad_port)
