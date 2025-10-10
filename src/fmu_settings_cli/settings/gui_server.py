"""Functionality to start the GUI server."""

from fmu_settings_gui import run_server

from .constants import APP_REG_PORTS, GUI_PORT, HOST


def start_gui_server(
    token: str,
    host: str = HOST,
    port: int = GUI_PORT,
) -> None:
    """Starts the fmu-settings-gui server.

    If the port for the gui server is not one registered in the Azure App Registration,
    the application will exit.

    Args:
        token: The authentication token the GUI uses
        host: The host to bind the server to
        port: The port to run the server on
    """
    if port not in APP_REG_PORTS:
        known_ports_str = ", ".join(str(i) for i in APP_REG_PORTS)
        raise ValueError(
            f"Port {port} is not known by the Azure App registration. "
            f"Use one of {known_ports_str}."
        )

    try:
        print(f"Starting FMU Settings GUI server on {host}:{port}...")
        run_server(host, port)
    except Exception as e:
        raise RuntimeError(f"Could not start GUI server: {e}") from e
