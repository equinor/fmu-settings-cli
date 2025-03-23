"""Functionality to start the API server."""

import sys

from fmu.settings.api import run_server


def start_api_server(
    token: str,
    host: str = "127.0.0.1",
    port: int = 8001,
    frontend_host: str = "localhost",
    frontend_port: int = 8000,
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
