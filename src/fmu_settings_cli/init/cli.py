"""The 'init' command."""

from pathlib import Path
from typing import Annotated

import typer
from fmu.settings._global_config import (
    InvalidGlobalConfigurationError,
    find_global_config,
)
from fmu.settings._init import (
    InvalidFMUProjectPathError,
    init_fmu_directory,
)
from pydantic import ValidationError

from fmu_settings_cli.prints import (
    error,
    info,
    success,
    validation_error,
    validation_warning,
    warning,
)

init_cmd = typer.Typer(
    help="Initialize a .fmu directory in this directory if it contains an FMU model.",
    add_completion=True,
)


@init_cmd.callback(invoke_without_command=True)
def init(  # noqa: PLR0912
    ctx: typer.Context,
    force: Annotated[
        bool,
        typer.Option(
            "--force",
            help="Skip validating that we are creating this in the right place.",
            show_default=False,
        ),
    ] = False,
) -> None:
    """The main entry point for the init command."""
    if ctx.invoked_subcommand is not None:  # pragma: no cover
        return

    cwd = Path.cwd()

    fmu_dir_path = cwd / ".fmu"

    try:
        fmu_dir = init_fmu_directory(cwd, force=force)
    except InvalidFMUProjectPathError as e:
        error(
            "Unable to create .fmu directory.",
            reason=str(e),
        )
        raise typer.Abort from e
    except FileExistsError as e:
        error(
            "Unable to create .fmu directory.",
            reason=(
                f"{fmu_dir_path} already exists"
                if fmu_dir_path.is_dir()
                else (
                    f"{fmu_dir_path} exists but is not a directory"
                    if fmu_dir_path.exists()
                    else str(e)
                )
            ),
            suggestion=(
                "You do not need to initialize a .fmu in this directory."
                if fmu_dir_path.is_dir()
                else "Delete this file before initializing .fmu."
            ),
        )
        raise typer.Abort from e
    except PermissionError as e:
        error(
            "Unable to create .fmu directory.",
            reason=str(e),
            suggestion="You are lacking permissions to create files in this directory",
        )
        raise typer.Abort from e
    except ValidationError as e:
        validation_error(e, "Unable to create .fmu directory.")
        raise typer.Abort from e
    except Exception as e:
        error(
            "Unable to create .fmu directory",
            reason=str(e),
            suggestion=(
                "This is an unknown error. Please report this as a bug in "
                "'#fmu-settings' on Slack, Viva Engage, or the FMU Portal."
            ),
        )
        raise typer.Abort from e

    try:
        global_config = find_global_config(cwd)
    except ValidationError as e:
        validation_warning(
            e,
            "Unable to import masterdata.",
            reason="Validation of the global config/global variables failed.",
            suggestion=(
                "You will need to establish valid SMDA masterdata in FMU "
                "Settings by running and opening 'fmu settings'."
            ),
        )
    except InvalidGlobalConfigurationError:
        warning(
            "Unable to import masterdata.",
            reason=(
                "The global config contains data that is not valid SMDA "
                "masterdata. This can happen when the file contains placeholder "
                "values or Drogon data."
            ),
            suggestion=(
                "You will need to establish valid SMDA masterdata in FMU "
                "Settings by running and opening 'fmu settings'."
            ),
        )
    else:
        if global_config:
            success(
                "Successfully imported access, masterdata, model from global config."
            )

    if fmu_dir.config.load().masterdata is not None:
        info(
            "Project stratigraphy was not imported by 'fmu init'.",
            suggestion=(
                "Open 'fmu settings' to import stratigraphy from RMS and map it "
                "to SMDA."
            ),
        )
    success("All done! You can now use the 'fmu settings' application.")
