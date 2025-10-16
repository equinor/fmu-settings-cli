"""The 'settings' command."""

import contextlib
import signal
import webbrowser
from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import Annotated

import typer

from fmu_settings_cli.prints import error, info, success

from ._utils import (
    create_authorized_url,
    ensure_port,
    generate_auth_token,
)
from .api_server import start_api_server
from .constants import API_PORT, GUI_PORT, HOST
from .gui_server import start_gui_server

settings_app = typer.Typer(
    help="Start the FMU Settings application and manage your FMU model's settings.",
    add_completion=True,
)


@settings_app.command()
def gui(
    gui_port: Annotated[
        int,
        typer.Option("--gui-port", help="Port to run the GUI on.", show_default=True),
    ] = GUI_PORT,
    host: Annotated[
        str,
        typer.Option(
            "--host",
            help="Host to bind the API and GUI servers to.",
            show_default=False,
        ),
    ] = HOST,
) -> None:
    """Start the FMU Settings GUI only. Used for development."""
    ensure_port(gui_port)
    token = generate_auth_token()
    start_gui_server(token, host=host, port=gui_port)


@settings_app.command()
def api(  # noqa: PLR0913
    api_port: Annotated[
        int,
        typer.Option("--api-port", help="Port to run the API on.", show_default=True),
    ] = API_PORT,
    gui_port: Annotated[
        int,
        typer.Option("--gui-port", help="Port to run the GUI on.", show_default=True),
    ] = GUI_PORT,
    host: Annotated[
        str,
        typer.Option(
            "--host",
            help="Host to bind the API and GUI servers to.",
            show_default=False,
        ),
    ] = HOST,
    reload: Annotated[
        bool,
        typer.Option(
            "--reload",
            help="Enable auto-reload. Used for development.",
            show_default=False,
        ),
    ] = False,
    print_token: Annotated[
        bool,
        typer.Option(
            "--print-token",
            help=(
                "Prints the token the API requires for authorization. "
                "Used for development."
            ),
            show_default=False,
            envvar="FMU_SETTINGS_PRINT_TOKEN",
        ),
    ] = False,
    print_url: Annotated[
        bool,
        typer.Option(
            "--print-url",
            help=(
                "Prints the authorized URL a user would be directed to. "
                "Used for development."
            ),
            show_default=False,
            envvar="FMU_SETTINGS_PRINT_URL",
        ),
    ] = False,
) -> None:
    """Start the FMU Settings API only. Used for development."""
    ensure_port(api_port)
    token = generate_auth_token()

    if print_token:
        info("API Token:", token)
    if print_url:
        info("Authorized URL:", create_authorized_url(token, host, gui_port))

    start_api_server(
        token,
        host=host,
        port=api_port,
        frontend_host=host,
        frontend_port=gui_port,
        reload=reload,
    )


@settings_app.callback(invoke_without_command=True)
def settings(
    ctx: typer.Context,
    api_port: Annotated[
        int,
        typer.Option("--api-port", help="Port to run the API on.", show_default=True),
    ] = API_PORT,
    gui_port: Annotated[
        int,
        typer.Option("--gui-port", help="Port to run the GUI on.", show_default=True),
    ] = GUI_PORT,
    host: Annotated[
        str,
        typer.Option(
            "--host",
            help="Host to bind the API and GUI servers to.",
            show_default=False,
        ),
    ] = HOST,
    reload: Annotated[
        bool,
        typer.Option(
            "--reload",
            help="Enable auto-reload. Used for development.",
            show_default=False,
        ),
    ] = False,
) -> None:
    """The main entry point for the settings command."""
    if ctx.invoked_subcommand is not None:
        return

    for port in [api_port, gui_port]:
        ensure_port(port)

    token = generate_auth_token()
    start_api_and_gui(token, api_port, gui_port, host, reload)


def init_worker() -> None:  # pragma: no cover
    """Initializer to ignore signal interrupts on workers."""
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    signal.signal(signal.SIGTERM, signal.SIG_IGN)


def start_api_and_gui(
    token: str, api_port: int, gui_port: int, host: str, reload: bool
) -> None:
    """Starts both API and GUI as concurrent processes.

    Args:
        token: Authentication token shared to api and gui
        api_port: The port the API will bind to
        gui_port: The port the GUI will bind to
        host: The host both the API and GUI will bind to
        reload: If True, the API will reload on any code changes
    """
    with ProcessPoolExecutor(max_workers=3, initializer=init_worker) as executor:
        try:
            server_futures = {
                "api": executor.submit(
                    start_api_server,
                    token,
                    host=host,
                    port=api_port,
                    frontend_host=host,
                    frontend_port=gui_port,
                    reload=reload,
                ),
                "gui": executor.submit(
                    start_gui_server,
                    token,
                    host=host,
                    port=gui_port,
                ),
            }

            # Does not need to be executed as a separate process, but causes this
            # function to be called _after_ starting API and GUI. It finishes
            # immediately.
            browser_future = executor.submit(
                webbrowser.open,
                create_authorized_url(token, host, gui_port),
            )
            browser_future.result()

            is_start_up = True
            while True:
                try:
                    # Check once a half second if either the GUI or API process have
                    # completed. This will typically mean crashed or otherwise failed.
                    completed_future = next(
                        as_completed(server_futures.values(), timeout=0.5)
                    )
                    try:
                        service = next(
                            name
                            for name, f in server_futures.items()
                            if f is completed_future
                        ).upper()
                        completed_future.result()
                        error(
                            f"{service} unexpectedly exited. Please report this "
                            "as a bug",
                        )
                    except SystemExit as e:
                        # If a port is in use, uvicorn will raise a SystemExit as this
                        # is a fatal error. Unfortunately the exact message is emitted
                        # as an ERROR log statement, not inside the exception itself.
                        required_port = gui_port if service == "GUI" else api_port
                        error(
                            f"{service} exited with exit code {e}. Usually this "
                            "means that another application is already using "
                            f"port {required_port}.",
                        )
                    except Exception as e:
                        # This is the exception raised by start_[api, gui]_server
                        error(f"{service} failed with: {e}")
                    break
                except Exception:
                    # This is the valid case, where the server future has not completed
                    # within the 0.5 second timeout, and so raises a TimeoutError. But
                    # grab all exceptions more broadly.
                    if is_start_up:
                        # Defer this message until we are certain GUI/API have started
                        # without initial errors.
                        success("FMU Settings is running. Press CTRL+C to quit")
                        is_start_up = False
                    continue

        except KeyboardInterrupt:
            info("Shutting down FMU Settings ...")
        finally:
            for future in server_futures.values():
                future.cancel()

            # Uses the internal pid->process mapping. The executor API does not offer a
            # way to retrieve this information, oddly. There is a small possibility this
            # breaks in a future version of Python, although it is unlikely as it would
            # disrupt a great deal of CPython code.
            for process in executor._processes.values():
                with contextlib.suppress(Exception):
                    process.terminate()

            executor.shutdown(wait=False, cancel_futures=True)
