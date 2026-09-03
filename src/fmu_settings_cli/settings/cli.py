"""The 'settings' command."""

from pathlib import Path
from typing import Annotated
from uuid import uuid4

import typer

from fmu_settings_cli.prints import info

from ._utils import (
    create_authorized_url,
    ensure_port,
    generate_auth_token,
)
from .api_server import start_api_server
from .constants import APP_PORT, HOST, AppPort, GuiPort, LogLevel
from .main import start_app


def _get_static_directory() -> Path:
    """Get the packaged GUI directory without loading it for API-only commands."""
    from fmu_settings_gui import get_static_directory  # noqa: PLC0415 lazy load

    return get_static_directory()


settings_app = typer.Typer(
    help=(
        "Start the FMU Settings application and manage your FMU model's settings.\n\n"
        "Run 'fmu settings' to use the application. The commands below are not "
        "recommended or necessary for normal users in normal usage."
    ),
    add_completion=True,
)


@settings_app.command()
def api(  # noqa: PLR0913
    gui_port: Annotated[
        GuiPort,
        typer.Option("--gui-port", help="Port to run the GUI on.", show_default=True),
    ] = APP_PORT,
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
    enable_telemetry: Annotated[
        bool,
        typer.Option(
            "--telemetry",
            help="Send API telemetry to Azure. Used for development testing.",
            show_default=False,
        ),
    ] = False,
    log_level: Annotated[
        LogLevel,
        typer.Option(
            "--log-level",
            help="The minimum log level to display in the terminal.",
            envvar="FMU_SETTINGS_LOG_LEVEL",
        ),
    ] = "critical",
) -> None:
    """Start the FMU Settings API only. Used for development."""
    ensure_port(APP_PORT)
    token = generate_auth_token()

    if print_token:
        info("API Token:", token)
    if print_url:
        info("Authorized URL:", create_authorized_url(token, host, gui_port))

    start_api_server(
        token,
        host=host,
        port=APP_PORT,
        frontend_host=host,
        frontend_port=gui_port,
        reload=reload,
        log_level=log_level,
        enable_telemetry=enable_telemetry,
        run_id=str(uuid4()) if enable_telemetry else None,
        environment="development",
    )


@settings_app.callback(invoke_without_command=True)
def settings(
    ctx: typer.Context,
    port: Annotated[
        AppPort,
        typer.Option(
            "--port",
            help="Port to run the application on.",
            show_default=True,
        ),
    ] = APP_PORT,
    host: Annotated[
        str,
        typer.Option(
            "--host",
            help="Host to bind the application server to.",
            show_default=False,
        ),
    ] = HOST,
    log_level: Annotated[
        LogLevel,
        typer.Option(
            "--log-level",
            help="The minimum log level to display in the terminal.",
            envvar="FMU_SETTINGS_LOG_LEVEL",
        ),
    ] = "critical",
) -> None:
    """The main entry point for the settings command."""
    if ctx.invoked_subcommand is not None:
        return

    ensure_port(port)

    token = generate_auth_token()
    start_app(
        token,
        port=port,
        host=host,
        log_level=log_level,
        frontend_directory=_get_static_directory(),
        run_id=str(uuid4()),
        environment="production",
    )
