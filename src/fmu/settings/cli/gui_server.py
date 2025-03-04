"""Functionality to start the GUI server."""

import sys

from fmu.settings.gui import run_server


def start_gui_server(
    host: str = "127.0.0.1",
    port: int = 8000,
) -> None:
    """Starts the fmu-settings-api server.

    Args:
        host (str): The host to bind the server to
        port (int): The port to run the server on
    """
    try:
        print(f"Starting FMU Settings GUI server on {host}:{port}...")
        run_server(host, port)
    except Exception as e:
        print(f"Could not start GUI server: {e}")
        sys.exit(1)
