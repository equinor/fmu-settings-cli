"""The 'settings' command."""

import argparse
import contextlib
import os
import signal
import sys
import webbrowser
from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import Final

from fmu_settings_cli.types import SubparserType

from ._utils import (
    create_authorized_url,
    ensure_port,
    generate_auth_token,
)
from .api_server import start_api_server
from .constants import API_PORT, GUI_PORT, HOST
from .gui_server import start_gui_server

CMD: Final[str] = "settings"


def add_parser(cmd_parser: SubparserType) -> argparse.ArgumentParser:
    """Add the subparser for this command."""
    parser = cmd_parser.add_parser(
        CMD,
        help="Start the FMU Settings application to manage your FMU project's setting",
    )

    parser.add_argument(
        "--api-port",
        type=int,
        default=API_PORT,
        help=f"Port to run the API on (default: {API_PORT})",
    )
    parser.add_argument(
        "--gui-port",
        type=int,
        default=GUI_PORT,
        help=f"Port to run the GUI on (default: {GUI_PORT})",
    )
    parser.add_argument(
        "--host",
        type=str,
        default=HOST,
        help=f"Host to bind the API and GUI servers to (default: {HOST})",
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        default=False,
        help="Enable auto-reload for development",
    )

    subparsers = parser.add_subparsers(dest="subcommand", help="Subcommand to run")

    # API subparser
    api_parser = subparsers.add_parser("api", help="Start the API server")
    api_parser.add_argument(
        "--port",
        type=int,
        default=API_PORT,
        help=f"Port to run the API on (default: {API_PORT})",
    )
    api_parser.add_argument(
        "--host",
        type=str,
        default=HOST,
        help=f"Host to bind the API server to (default: {HOST})",
    )
    api_parser.add_argument(
        "--gui-host",
        type=str,
        default=HOST,
        help="Host the GUI sends requests from. Sets the CORS host.",
    )
    api_parser.add_argument(
        "--gui-port",
        type=int,
        default=GUI_PORT,
        help="Port the GUI sends requests from. Sets the CORS port.",
    )
    api_parser.add_argument(
        "--reload",
        action="store_true",
        default=False,
        help="Enable auto-reload for development",
    )
    api_parser.add_argument(
        "--print-token",
        action="store_true",
        help=(
            "Prints the token the API requires for authorization. Used for development."
        ),
    )
    api_parser.add_argument(
        "--print-url",
        action="store_true",
        help=(
            "Prints the authorized URL a user would be directed to. "
            "Used for development."
        ),
    )

    # GUI subparser
    gui_parser = subparsers.add_parser("gui", help="Start the GUI server")
    gui_parser.add_argument(
        "--port",
        type=int,
        default=GUI_PORT,
        help=f"Port to run the GUI on (default: {GUI_PORT})",
    )
    gui_parser.add_argument(
        "--host",
        type=str,
        default=HOST,
        help=f"Host to bind the GUI server to (default: {HOST})",
    )

    return parser


def init_worker() -> None:  # pragma: no cover
    """Initializer to ignore signal interrupts on workers."""
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    signal.signal(signal.SIGTERM, signal.SIG_IGN)


def start_api_and_gui(token: str, args: argparse.Namespace) -> None:
    """Starts both API and GUI as concurrent processes.

    Args:
        token: Authentication token shared to api and gui
        args: The arguments taken in from invocation
    """
    with ProcessPoolExecutor(max_workers=3, initializer=init_worker) as executor:
        try:
            server_futures = {
                "api": executor.submit(
                    start_api_server,
                    token,
                    host=args.host,
                    port=args.api_port,
                    frontend_host=args.host,
                    frontend_port=args.gui_port,
                    reload=args.reload,
                ),
                "gui": executor.submit(
                    start_gui_server,
                    token,
                    host=args.host,
                    port=args.gui_port,
                ),
            }

            # Does not need to be executed as a separate process, but causes this
            # function to be called _after_ starting API and GUI. It finishes
            # immediately.
            browser_future = executor.submit(
                webbrowser.open,
                create_authorized_url(token, args.host, args.gui_port),
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
                        print(
                            f"Error: {service} unexpectedly exited. Please report this "
                            "as a bug",
                            file=sys.stderr,
                        )
                    except SystemExit as e:
                        # If a port is in use, uvicorn will raise a SystemExit as this
                        # is a fatal error. Unfortunately the exact message is emitted
                        # as an ERROR log statement, not inside the exception itself.
                        required_port = (
                            args.gui_port if service == "GUI" else args.api_port
                        )
                        print(
                            f"Error: {service} exited with exit code {e}. Usually this "
                            "means that another application is already using port "
                            f"{required_port}.",
                            file=sys.stderr,
                        )
                    except Exception as e:
                        # This is the exception raised by start_[api, gui]_server
                        print(f"Error: {service} failed with: {e}", file=sys.stderr)
                    break
                except Exception:
                    # This is the valid case, where the server future has not completed
                    # within the 0.5 second timeout, and so raises a TimeoutError. But
                    # grab all exceptions more broadly.
                    if is_start_up:
                        # Defer this message until we are certain GUI/API have started
                        # without initial errors.
                        print("FMU Settings is running. Press CTRL+C to quit")
                        is_start_up = False
                    continue

        except KeyboardInterrupt:
            print("\nShutting down FMU Settings...")
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


def run(args: argparse.Namespace) -> None:
    """The main entry point for the settings command."""
    token = generate_auth_token()

    if args.subcommand == "api":
        if args.print_token or os.getenv("FMU_SETTINGS_PRINT_TOKEN"):
            print("API Token:", token)
        if args.print_url or os.getenv("FMU_SETTINGS_PRINT_URL"):
            print(
                "Authorized URL:",
                create_authorized_url(token, args.gui_host, args.gui_port),
            )
        ensure_port(args.port)
        start_api_server(
            token,
            host=args.host,
            port=args.port,
            frontend_host=args.gui_host,
            frontend_port=args.gui_port,
            reload=args.reload,
        )
    elif args.subcommand == "gui":
        ensure_port(args.port)
        start_gui_server(token, host=args.host, port=args.port)
    else:
        for port in [args.api_port, args.gui_port]:
            ensure_port(port)
        start_api_and_gui(token, args)
