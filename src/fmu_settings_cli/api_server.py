"""Functionality to start the API server."""

import sys

from fmu_settings_api import run_server

from .constants import API_PORT, GUI_PORT, HOST


def start_api_server(
    token: str,
    host: str = HOST,
    port: int = API_PORT,
    frontend_host: str = HOST,
    frontend_port: int = GUI_PORT,
) -> None:
    """Starts the fmu-settings-api server.

    Args:
        token: The authentication token the API uses
        host: The host to bind the server to
        port: The port to run the server on
        frontend_host: The frontend host to allow (CORS)
        frontend_port: The frontend port to allow (CORS)
    """
    try:
        print(f"Starting FMU Settings API server on {host}:{port}...")
        run_server(
            token=token,
            host=host,
            port=port,
            frontend_host=frontend_host,
            frontend_port=frontend_port,
        )
    except Exception as e:
        print(f"Could not start API server: {e}")
        sys.exit(1)
