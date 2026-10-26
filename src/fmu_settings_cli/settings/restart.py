"""Confirm and stop an existing application before starting its replacement."""

import json
import os
import signal
import time
import urllib.request
from contextlib import suppress
from http.client import HTTPException

import typer

from fmu_settings_cli.prints import error, info, warning

from ._utils import get_process_on_port
from .constants import HOST, NO_PROCESS_PID

SHUTDOWN_TIMEOUT_SECONDS = 30


def ensure_fmu_settings(port: int, host: str = HOST) -> None:
    """Require the FMU Settings identifier from the health route."""
    try:
        with urllib.request.urlopen(
            f"http://{host}:{port}/health", timeout=2
        ) as response:
            payload: object = json.load(response)
            identified = (
                response.status == 200
                and isinstance(payload, dict)
                and payload.get("application") == "fmu-settings"
            )
    except (OSError, ValueError, HTTPException):
        identified = False

    if not identified:
        error(
            "Could not start FMU Settings.",
            reason=(
                "Another application may be running, "
                "or FMU Settings did not respond as expected."
            ),
            suggestion=(
                "If FMU Settings is already open, press Ctrl+C in the terminal "
                "where you started it. Then run 'fmu settings' again."
            ),
        )
        raise typer.Abort


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


def stop_process(port: int, host: str = HOST) -> None:
    """Stop the current FMU Settings listener before a replacement starts.

    Look up the listener again because it can change during confirmation.
    Return if no listener remains. Otherwise, verify the application identifier
    before sending SIGTERM. If the process has already stopped, check that
    the port is free.

    Wait up to 30 seconds for process exit, then check that the port is free.
    Abort if a lookup or identity check fails, a signal is denied, shutdown
    times out, or another listener takes the port. Never send SIGKILL.
    """
    info("Restarting FMU Settings ...")
    # The listener can change while the confirmation waits for the user.
    pid, _ = get_process_on_port(port)
    if pid == NO_PROCESS_PID:
        return

    ensure_fmu_settings(port, host)

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
    if listener_pid != NO_PROCESS_PID:
        error(
            "Could not start FMU Settings.",
            reason="Another app is still using the connection that FMU Settings needs.",
            suggestion="Please try again.",
        )
        raise typer.Abort
