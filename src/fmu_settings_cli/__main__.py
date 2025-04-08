"""The main entry point for fmu-settings-cli."""

import argparse
import hashlib
import os
import secrets
import signal
import sys
import webbrowser
from concurrent.futures import ProcessPoolExecutor

from .api_server import start_api_server
from .constants import API_PORT, GUI_PORT, HOST
from .gui_server import start_gui_server


def _parse_args(args: list[str] | None = None) -> argparse.Namespace:
    if args is None:
        args = sys.argv[1:]

    parser = argparse.ArgumentParser(
        description="FMU Settings - Manage your FMU project's settings"
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
        help="Enable auto-reload for development",
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

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
        help=(
            f"Host the GUI sends requests from. Sets the CORS host. (default: {HOST})"
        ),
    )
    api_parser.add_argument(
        "--gui-port",
        type=int,
        default=GUI_PORT,
        help=(
            "Port the GUI sends requests from. Sets the CORS port. "
            f"(default: {GUI_PORT})"
        ),
    )
    api_parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload for development",
    )
    api_parser.add_argument(
        "--print-token",
        action="store_true",
        help=(
            "Prints the token the API requires for authorization. Used for development."
        ),
    )

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

    return parser.parse_args(args)


def generate_auth_token() -> str:
    """Generates an authentication token.

    This token is used to validate requests between the API and the GUI.

    Returns:
        A 256-bit token
    """
    random_bytes = secrets.token_hex(32)
    return hashlib.sha256(random_bytes.encode()).hexdigest()


def init_worker() -> None:
    """Initializer to ignore signal interrupts on workers."""
    signal.signal(signal.SIGINT, signal.SIG_IGN)


def start_api_and_gui(token: str, args: argparse.Namespace) -> None:
    """Starts both API and GUI as concurrent processes.

    Args:
        token: Authentication token shared to api and gui
        args: The arguments taken in from invocation
    """
    with ProcessPoolExecutor(max_workers=3, initializer=init_worker) as executor:
        api_future = executor.submit(
            start_api_server,
            token,
            host=args.host,
            port=args.api_port,
            frontend_host=args.host,
            frontend_port=args.gui_port,
        )
        gui_future = executor.submit(
            start_gui_server,
            token,
            host=args.host,
            port=args.gui_port,
        )
        # Does not need to be executed as a separate process, but causes this function
        # to be called _after_ starting API and GUI. It finishes immediately
        browser_future = executor.submit(
            webbrowser.open, f"http://{args.host}:{args.gui_port}/#token={token}"
        )
        try:
            browser_future.result()
            print("FMU Settings is running. Press CTRL+C to quit")
            # These block
            api_future.result()
            gui_future.result()
        except KeyboardInterrupt:
            print("\nShutting down FMU Settings...")
            api_future.cancel()
            gui_future.cancel()
            executor.shutdown(wait=True)


def main(test_args: list[str] | None = None) -> None:
    """The main entry point."""
    args = _parse_args(test_args)

    token = generate_auth_token()
    match args.command:
        case "api":
            if args.print_token or os.getenv("FMU_SETTINGS_PRINT_TOKEN"):
                print("API Token:", token)
            start_api_server(
                token,
                host=args.host,
                port=args.port,
                frontend_host=args.gui_host,
                frontend_port=args.gui_port,
            )
        case "gui":
            start_gui_server(token, host=args.host, port=args.port)
        case _:
            start_api_and_gui(token, args)


if __name__ == "__main__":
    main()
