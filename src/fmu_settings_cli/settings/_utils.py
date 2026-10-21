"""Simple utility functions needed to start the application."""

import hashlib
import secrets
import subprocess

import typer

from fmu_settings_cli.prints import error

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
    """Get the process listening on a TCP port.

    Returns:
        int, str tuple with the pid and command used to launch the process.  Returns
            INVALID_PID (-1), "Error" if no listener was found.
    """
    try:
        result = subprocess.run(
            ["lsof", "-nP", f"-iTCP:{port}", "-sTCP:LISTEN", "-t"],
            capture_output=True,
            text=True,
            check=True,
        )
        pids = result.stdout.strip().split("\n")
        if pids and pids[0]:
            pid = int(pids[0])
            try:
                ps_result = subprocess.run(
                    ["ps", "-p", str(pid), "-o", "comm="],
                    capture_output=True,
                    text=True,
                    check=True,
                )
            except (OSError, subprocess.CalledProcessError):
                return pid, "unknown"
            return pid, ps_result.stdout.strip()
    except subprocess.CalledProcessError as exc:
        # lsof uses status 1 for both no matches and errors.
        if exc.returncode != 1 or exc.stdout or exc.stderr:
            error(
                "Could not check whether FMU Settings is running.",
                suggestion="Please try again.",
            )
            raise typer.Abort from exc
    except OSError as exc:
        error(
            "Could not check whether FMU Settings is running.",
            suggestion="Please try again.",
        )
        raise typer.Abort from exc
    return (INVALID_PID, "Error")


def ensure_port(port: int) -> None:
    """Checks if a required port is open and fails gracefully if not."""
    pid, process = get_process_on_port(port)
    # Invalid pid means no process running
    if pid == INVALID_PID:
        return

    error(
        f"fmu-settings requires port {port} but it is currently in use.",
        reason=f"Currently used by PID: {pid}, command: {process}",
    )
    raise typer.Abort
