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

from .model_diff import display_model_diff, get_model_diff

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

    from_config = from_fmu.config.load()
    to_config = to_fmu.config.load()

    changes = get_model_diff(to_config, from_config)
    if not changes:
        success("No changes detected.")
        raise typer.Exit(0)

    display_model_diff(changes, to_config, from_config)

    warning(
        f"The above changes will be merged\n"
        f"  [bold][cyan]→[/cyan] From[/bold]: {str(from_dir)}\n"
        f"  [bold][cyan]→[/cyan] To[/bold]: {str(to_dir)}\n"
    )
    confirmed = typer.confirm("Merge these changes?")
    if not confirmed:
        raise typer.Abort

    # TODO: Be more granular in updated. We don't want to update the 'created_at' or
    # 'created_by', for example. But fine for an initial implementation.
    to_fmu.update_config(from_config.model_dump())
    success(f"All done! {from_dir} has been sync'd to {to_dir}.")
