"""The 'init' command."""

from pathlib import Path
from typing import TYPE_CHECKING, Annotated

import typer
from fmu.settings._global_config import (
    InvalidGlobalConfigurationError,
    find_global_config,
    load_global_configuration_if_present,
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

if TYPE_CHECKING:
    from fmu.datamodels.fmu_results.global_configuration import GlobalConfiguration

init_cmd = typer.Typer(
    help="Initialize a .fmu directory in this directory if it contains an FMU model.",
    add_completion=True,
)


def _find_global_config_source(base_path: Path) -> Path | None:
    """Find which global config file would have been imported."""
    global_variables_path = base_path / "fmuconfig/output/global_variables.yml"
    if global_variables_path.exists() and load_global_configuration_if_present(
        global_variables_path
    ):
        return global_variables_path

    input_dir = base_path / "fmuconfig/input"
    if not input_dir.exists():
        return None

    for global_config_path in input_dir.glob("**/global*.yml"):
        if load_global_configuration_if_present(global_config_path, fmu_load=True):
            return global_config_path

    return None


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

    global_config: GlobalConfiguration | None = None
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

    if global_config:
        imported_sections = ", ".join(
            section
            for section in ("access", "masterdata", "model")
            if getattr(global_config, section) is not None
        )
        source_suffix = (
            f" from {global_config_source}"
            if (global_config_source := _find_global_config_source(cwd))
            else ""
        )
        success(f"Successfully imported {imported_sections}{source_suffix}.")

    try:
        fmu_dir = init_fmu_directory(cwd, global_config=global_config, force=force)
    except InvalidFMUProjectPathError as e:
        error(
            "Unable to create .fmu directory.",
            reason=str(e),
        )
        raise typer.Abort from e
    except FileExistsError as e:
        error(
            "Unable to create .fmu directory.",
            reason=str(e),
            suggestion="You do not need to initialize a .fmu in this directory.",
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

    if fmu_dir.config.load().masterdata is not None:
        info(
            "Project stratigraphy was not imported by 'fmu init'.",
            suggestion=(
                "Open 'fmu settings' to import stratigraphy from RMS and map it "
                "to SMDA."
            ),
        )
    success("All done! You can now use the 'fmu settings' application.")
