"""The 'sync' command."""

from pathlib import Path
from typing import Annotated

import typer
from fmu.settings import find_nearest_fmu_directory, get_fmu_directory
from pydantic import ValidationError

from fmu_settings_cli.prints import (
    error,
    success,
    validation_error,
    warning,
)

from .model_diff import display_model_diff

sync_cmd = typer.Typer(
    help=(
        "Sync the settings and configuration of one FMU revision to another.\n\n"
        "Currently this syncs only the .fmu configuration files."
    ),
    add_completion=True,
)


@sync_cmd.callback(invoke_without_command=True)
def sync(
    from_dir: Annotated[
        Path,
        typer.Option(
            ...,
            "--from",
            "-f",
            help="Path to FMU Setting revision to sync *from*",
            default_factory=lambda: Path.cwd(),
        ),
    ],
    ctx: typer.Context,
    to_dir: Annotated[
        Path,
        typer.Option(
            ...,
            "--to",
            "-t",
            help="Path to FMU Setting revision to sync *to*",
        ),
    ],
) -> None:
    """The main entry point for the sync command."""
    if ctx.invoked_subcommand is not None:  # pragma: no cover
        return

    try:
        from_fmu = find_nearest_fmu_directory(from_dir)
    except Exception as e:
        error(
            "Unable to find a known and valid FMU project to sync [bold]from[/bold]",
            reason=str(e),
            suggestion=(
                "'cd' into the correct directory, or provide the path to the "
                "revision you are sync [italic]from[/italic]"
            ),
        )
        raise typer.Abort from e

    try:
        to_fmu = get_fmu_directory(to_dir)
    except ValidationError as e:
        validation_error(
            e,
            "Unable to load [bold]to[/bold] FMU Directory",
            reason="Validation of its configuration failed.",
            suggestion="You may have tried to sync to an incorrect directory path.",
        )
    except Exception as e:
        error(
            "Unable to find an FMU Settings configuration to sync [bold]to[/bold]",
            reason=str(e),
            suggestion=(
                "Provide a path to the revision you are syncing [italic]to[/italic], "
                "i.e. a master revision directory."
            ),
        )
        raise typer.Abort from e

    changes = to_fmu.get_dir_diff(from_fmu.path.parent)

    if all(len(change_list) == 0 for change_list in changes.values()):
        success("No changes detected.")
        raise typer.Exit(0)

    for resource, change_list in changes.items():
        display_model_diff(resource, change_list)

    from_dir_abs = from_dir.absolute()
    to_dir_abs = to_dir.absolute()

    warning(
        f"The above changes will be merged\n"
        f"  [bold][cyan]→[/cyan] From[/bold]: {str(from_dir_abs)}\n"
        f"  [bold][cyan]→[/cyan] To[/bold]: {str(to_dir_abs)}\n"
    )
    confirmed = typer.confirm("Merge these changes?")
    if not confirmed:
        raise typer.Abort

    to_fmu.sync_dir(from_fmu.path.parent)
    success(f"All done! {from_dir_abs} has been sync'd to {to_dir_abs}.")
