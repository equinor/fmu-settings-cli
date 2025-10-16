"""The 'init' command."""

import contextlib
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Final

import typer
from fmu.settings._global_config import (
    InvalidGlobalConfigurationError,
    find_global_config,
)
from fmu.settings._init import init_fmu_directory, init_user_fmu_directory
from pydantic import ValidationError
from rich.table import Table

from fmu_settings_cli.prints import error, validation_error

if TYPE_CHECKING:
    from fmu.datamodels.fmu_results.global_configuration import GlobalConfiguration


init_cmd = typer.Typer(
    help="Initialize a .fmu directory in this directory if it contains an FMU model.",
    add_completion=True,
)

REQUIRED_FMU_PROJECT_SUBDIRS: Final[list[str]] = ["ert"]


def is_fmu_project(path: Path) -> tuple[bool, list[str]]:
    """Ensures the provided directory looks like an FMU project.

    Args:
        path: The directory to check

    Returns:
        Tuple of bool and list of strings, indicating whether the provided path does or
        does not appear to be a valid FMU project, and what directories are lacking for
        it to be so, respectively.
    """
    missing: list[str] = []
    for dir_name in REQUIRED_FMU_PROJECT_SUBDIRS:
        dir_ = path / dir_name
        if not dir_.exists() or not dir_.is_dir():
            missing.append(dir_name)

    return len(missing) == 0, missing


@init_cmd.callback(invoke_without_command=True)
def init(
    ctx: typer.Context,
    force: Annotated[
        bool,
        typer.Option(
            "--force",
            help="Skip validating that we are creating this in the right place.",
            show_default=False,
        ),
    ] = False,
    skip_config_import: Annotated[
        bool,
        typer.Option(
            "--skip-config-import",
            help=(
                "Skip searching for and importing masterdata set in the global "
                "configuration or global variables."
            ),
            show_default=False,
        ),
    ] = False,
) -> None:
    """The main entry point for the init command."""
    if ctx.invoked_subcommand is not None:
        return

    with contextlib.suppress(FileExistsError):
        init_user_fmu_directory()

    cwd = Path.cwd()

    if not force:
        has_all_fmu_subdirs, missing_dirs = is_fmu_project(cwd)
        if not has_all_fmu_subdirs:
            dirs_table = Table("Directory")
            for dir_ in missing_dirs:
                dirs_table.add_row(dir_)

            error(
                f"This directory ({cwd}) does not appear to be an FMU project. "
                "Expected the following directories:",
                dirs_table,
            )
            raise typer.Abort

    global_config: GlobalConfiguration | None = None
    if not skip_config_import:
        try:
            global_config = find_global_config(cwd)
        except ValidationError as e:
            validation_error(
                e,
                "Unable to import existing masterdata.",
                reason="Validation of the global config/global variables failed.",
                suggestion=(
                    "Skip importing by running 'fmu init --skip-config-import' to "
                    "proceed. You will need to establish valid SMDA masterdata in FMU "
                    "Settings by running and opening 'fmu settings'."
                ),
            )
            raise typer.Abort from e
        except InvalidGlobalConfigurationError as e:
            error(
                "Unable to import existing masterdata.",
                reason=str(e),
                suggestion=(
                    "Skip importing by running 'fmu init --skip-config-import' to "
                    "proceed. You will need to establish valid SMDA masterdata in FMU "
                    "Settings by running and opening 'fmu settings'."
                ),
            )
            raise typer.Abort from e

    init_fmu_directory(cwd, global_config=global_config)
