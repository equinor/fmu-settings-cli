"""The 'init' command."""

import argparse
import contextlib
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Final

from fmu.settings._global_config import find_global_config
from fmu.settings._init import init_fmu_directory, init_user_fmu_directory

from fmu_settings_cli.types import SubparserType

if TYPE_CHECKING:
    from fmu.datamodels.fmu_results.global_configuration import GlobalConfiguration

CMD: Final[str] = "init"

REQUIRED_FMU_PROJECT_SUBDIRS: Final[list[str]] = ["ert"]


def add_parser(cmd_parser: SubparserType) -> argparse.ArgumentParser:
    """Add the subparser for this command."""
    parser = cmd_parser.add_parser(
        CMD,
        help=(
            "Initialize a .fmu directory in the current FMU project revision directory."
        ),
    )

    parser.add_argument(
        "--skip-config-import",
        action="store_true",
        default=False,
        help=(
            "Skip searching for and importing masterdata set in the global "
            "configuration or global variables."
        ),
    )
    parser.add_argument(
        "--force",
        action="store_true",
        default=False,
        help="Skip validating that we are creating this in the right place.",
    )

    return parser


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


def run(args: argparse.Namespace) -> None:
    """The main entry point for the init command."""
    with contextlib.suppress(FileExistsError):
        init_user_fmu_directory()

    cwd = Path.cwd()

    if not args.force:
        has_all_fmu_subdirs, missing_dirs = is_fmu_project(cwd)
        if not has_all_fmu_subdirs:
            dirs_list = "\n - ".join(missing_dirs)
            sys.exit(
                f"Error: This directory ({cwd}) does not appear to be an FMU project. "
                "Expected the following directories:"
                f"\n - {dirs_list}",
            )

    global_config: GlobalConfiguration | None = None
    if not args.skip_config_import:
        try:
            global_config = find_global_config(cwd)
        except ValueError as e:
            sys.exit(
                f"Error: Unable to import existing masterdata."
                f"\n - Reason: {e}\n\n"
                "Skip importing by running 'fmu init --skip-config-import' to proceed. "
                "You will need to establish valid SMDA masterdata in FMU Settings by "
                "running and opening 'fmu settings'."
            )

    init_fmu_directory(cwd, global_config=global_config)
