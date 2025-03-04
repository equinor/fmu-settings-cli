"""Functionality to start the API server."""

import sys

from fmu.settings.api import run_server


def start_api_server(
    host: str = "127.0.0.1",
    port: int = 8001,
) -> None:
    """Starts the fmu-settings-api server.

    Args:
        host (str): The host to bind the server to
        port (int): The port to run the server on
        reload (bool): Whether to enable auto-reload
        wait (bool): Whether to wait for the server to complete (blocking)
    """
    try:
        print(f"Starting FMU Settings API server on {host}:{port}...")
        run_server()
    except Exception as e:
        print(f"Could not start API server: {e}")
        sys.exit(1)
