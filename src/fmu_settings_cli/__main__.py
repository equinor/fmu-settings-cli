"""The main entry point for fmu-settings-cli."""

import argparse
import hashlib
import secrets
import signal
import sys
import webbrowser
from concurrent.futures import ProcessPoolExecutor

from .api_server import start_api_server
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
        default=8001,
        help="Port to run the API on (default: 8001)",
    )
    parser.add_argument(
        "--gui-port",
        type=int,
        default=8000,
        help="Port to run the GUI on (default: 8000)",
    )
    parser.add_argument(
        "--host",
        type=str,
        default="127.0.0.1",
        help="Host to bind the servers to (default: 127.0.0.1)",
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
        default=8001,
        help="Port to run the API on (default: 8001)",
    )
    api_parser.add_argument(
        "--host",
        type=str,
        default="127.0.0.1",
        help="Host to bind the API server to (default: 127.0.0.1)",
    )
    api_parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload for development",
    )

    gui_parser = subparsers.add_parser("gui", help="Start the GUI server")
    gui_parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to run the GUI on (default: 8000)",
    )
    gui_parser.add_argument(
        "--host",
        type=str,
        default="localhost",
        help="Host to bind the GUI server to (default: localhost)",
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
            webbrowser.open, f"http://localhost:{args.gui_port}/#token={token}"
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
            start_api_server(token, host=args.host, port=args.port)
        case "gui":
            start_gui_server(token, host=args.host, port=args.port)
        case _:
            start_api_and_gui(token, args)


if __name__ == "__main__":
    main()
