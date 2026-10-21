"""Confirm and stop an existing application before starting its replacement."""

import os
import signal
import time
from contextlib import suppress

import typer

from fmu_settings_cli.prints import error, info, warning

from ._utils import get_process_on_port
from .constants import INVALID_PID

SHUTDOWN_TIMEOUT_SECONDS = 30


def confirm_restart() -> bool:
    """Explain the restart and require confirmation, defaulting to No."""
    warning(
        "FMU Settings is already running.\n\n"
        "Open the FMU Settings tab in your browser to continue.\n"
        "If you cannot find the tab, you can restart the app.\n"
        "Any unsaved changes may be lost when you restart."
    )
    typer.echo()
    info("Press Enter or type n to keep the current app running. Type y to restart.")
    try:
        return typer.confirm("Restart FMU Settings?", default=False)
    except typer.Abort:
        return False


def stop_process(port: int) -> None:
    """Send SIGTERM to the current listener and wait until the port is free."""
    info("Restarting FMU Settings ...")
    # The listener can change while the confirmation waits for the user.
    pid, _ = get_process_on_port(port)
    if pid == INVALID_PID:
        return

    try:
        with suppress(ProcessLookupError):
            os.kill(pid, signal.SIGTERM)

        deadline = time.monotonic() + SHUTDOWN_TIMEOUT_SECONDS
        while True:
            try:
                os.kill(pid, 0)
            except ProcessLookupError:
                break
            if time.monotonic() >= deadline:
                error(
                    "FMU Settings has not finished shutting down.",
                    reason=f"Shutdown exceeded {SHUTDOWN_TIMEOUT_SECONDS} seconds.",
                    suggestion="Wait a moment, then run 'fmu settings' again.",
                )
                raise typer.Abort
            time.sleep(0.2)
    except OSError as exc:
        error(
            "Could not restart FMU Settings.",
            reason="The running app could not be stopped.",
            suggestion=(
                "Press Ctrl+C in the terminal where you started the app, "
                "then run 'fmu settings' again."
            ),
        )
        raise typer.Abort from exc

    listener_pid, _ = get_process_on_port(port)
    if listener_pid != INVALID_PID:
        error(
            "Could not start FMU Settings.",
            reason="Another app is still using the connection that FMU Settings needs.",
            suggestion="Please try again.",
        )
        raise typer.Abort
