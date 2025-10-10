"""Simple utility functions needed to start the application."""

import hashlib
import secrets
import subprocess
import sys

from .constants import INVALID_PID


def generate_auth_token() -> str:
    """Generates an authentication token.

    This token is used to validate requests between the API and the GUI.

    Returns:
        A 256-bit token
    """
    random_bytes = secrets.token_hex(32)
    return hashlib.sha256(random_bytes.encode()).hexdigest()


def create_authorized_url(token: str, host: str, gui_port: int) -> str:
    """Creates the authorized URL a user will be directed to."""
    return f"http://{host}:{gui_port}/#token={token}"


def get_process_on_port(port: int) -> tuple[int, str]:
    """Gets the process using a particular port, if possible.

    Returns:
        int, str tuple with the pid and command used to launch the process.  Returns
            INVALID_PID (-1), "Error" if the check has failed, i.e., no process is
            running on the port.
    """
    try:
        result = subprocess.run(
            ["lsof", "-i", f":{port}", "-t"],
            capture_output=True,
            text=True,
            check=True,
        )
        pids = result.stdout.strip().split("\n")
        if pids and pids[0]:
            # Get the process name
            ps_result = subprocess.run(
                ["ps", "-p", pids[0], "-o", "comm="],
                capture_output=True,
                text=True,
                check=True,
            )
            return (int(pids[0]), ps_result.stdout.strip())
    except subprocess.CalledProcessError:
        pass
    return (INVALID_PID, "Error")


def ensure_port(port: int) -> None:
    """Checks if a required port is open and fails gracefully if not."""
    pid, process = get_process_on_port(port)
    # Invalid pid means no process running
    if pid == INVALID_PID:
        return

    sys.exit(
        f"Error: fmu-settings requires port {port} but it is currently in use.\n\n"
        f"Currently used by PID: {pid}, command: {process}"
    )
