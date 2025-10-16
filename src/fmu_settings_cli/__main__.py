"""The main entry point for fmu-settings-cli."""

import typer

from .init import init_cmd
from .settings import settings_app

app = typer.Typer(
    name="fmu",
    help="FMU Settings - Manage your FMU project",
    add_completion=True,
    no_args_is_help=True,
)

app.add_typer(init_cmd, name="init")
app.add_typer(settings_app, name="settings")


def main() -> None:
    """The main entry point."""
    app()


if __name__ == "__main__":  # pragma: no cover
    main()
