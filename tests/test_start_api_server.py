"""Tests for api_server.py."""

from unittest.mock import patch

import pytest

from fmu_settings_cli.__main__ import generate_auth_token
from fmu_settings_cli.api_server import start_api_server


def test_start_api_server() -> None:
    """Tests that start_api_server calls as expected."""
    token = generate_auth_token()
    with patch("fmu_settings_cli.api_server.run_server") as mock_run_server:
        start_api_server(token)
        mock_run_server.assert_called_once()


def test_start_api_server_fails() -> None:
    """Tests that start_api_server failing raises an exception."""
    token = generate_auth_token()
    with (
        patch(
            "fmu_settings_cli.api_server.run_server", side_effect=OSError("fail")
        ) as mock_run_server,
        pytest.raises(RuntimeError, match="Could not start API server: fail"),
    ):
        start_api_server(token)
        mock_run_server.assert_called_once()
