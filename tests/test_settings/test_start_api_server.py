"""Tests for api_server.py."""

from pathlib import Path
from unittest.mock import patch

import pytest

from fmu_settings_cli.settings._utils import generate_auth_token
from fmu_settings_cli.settings.api_server import start_api_server


def test_start_api_server() -> None:
    """Tests that start_api_server calls as expected."""
    token = generate_auth_token()
    with patch("fmu_settings_api.run_server") as mock_run_server:
        frontend_directory = Path("/frontend")
        start_api_server(token, frontend_directory=frontend_directory)
        mock_run_server.assert_called_once_with(
            token=token,
            host="localhost",
            port=8001,
            frontend_host="localhost",
            frontend_port=8000,
            reload=False,
            log_level="critical",
            frontend_directory=frontend_directory,
        )


def test_start_api_server_fails() -> None:
    """Tests that start_api_server failing raises an exception."""
    token = generate_auth_token()
    with (
        patch(
            "fmu_settings_api.run_server", side_effect=OSError("fail")
        ) as mock_run_server,
        pytest.raises(RuntimeError, match="Could not start API server: fail"),
    ):
        start_api_server(token)
        mock_run_server.assert_called_once()
