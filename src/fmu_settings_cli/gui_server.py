"""Functionality to start the GUI server."""

import sys

from fmu_settings_gui import run_server

from .constants import GUI_PORT, HOST


def start_gui_server(
    token: str,
    host: str = HOST,
    port: int = GUI_PORT,
) -> None:
    """Starts the fmu-settings-api server.

    Args:
        token: The authentication token the GUI uses
        host: The host to bind the server to
        port: The port to run the server on
    """
    try:
        print(f"Starting FMU Settings GUI server on {host}:{port}...")
        run_server(host, port)
    except Exception as e:
        print(f"Could not start GUI server: {e}")
        sys.exit(1)
