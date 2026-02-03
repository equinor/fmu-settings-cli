"""The 'copy' command."""

from typing import Annotated

import typer

from .copy import (
    DEFAULT_PROFILE,
    DEFAULT_THREADS,
    CopyArgs,
    run_copy,
)

copy_cmd = typer.Typer(
    help=(
        "Copy a FMU revision folder with selective filters and multithreading.\n\n"
        "This command mirrors the fmu_copy_revision script."
    ),
    add_completion=True,
)


@copy_cmd.callback(invoke_without_command=True)
def copy(  # noqa: PLR0913
    ctx: typer.Context,
    dryrun: Annotated[
        bool,
        typer.Option("--dryrun", help="Run dry run for testing", show_default=False),
    ] = False,
    all_: Annotated[
        bool,
        typer.Option(
            "--all",
            "-a",
            "-all",
            help="List all folders",
            show_default=False,
        ),
    ] = False,
    verbosity: Annotated[
        bool,
        typer.Option(
            "--verbose",
            "--verbosity",
            "-v",
            help="Enable logging (messages) for debugging",
            show_default=False,
        ),
    ] = False,
    cleanup: Annotated[
        bool,
        typer.Option(
            "--cleanup",
            help="Remove (cleanup) if target already exists, default is False.",
            show_default=False,
        ),
    ] = False,
    merge: Annotated[
        bool,
        typer.Option(
            "--merge",
            help=(
                "Try a rsync merge if target already exists, default is False. "
                "Note this operation is currently somewhat experimental. Cannot be "
                "combined with --cleanup"
            ),
            show_default=False,
        ),
    ] = False,
    skipestimate: Annotated[
        bool,
        typer.Option(
            "--skipestimate",
            "--skip",
            "-s",
            help="If present, skip estimation of current revision size.",
            show_default=False,
        ),
    ] = False,
    source: Annotated[
        str | None,
        typer.Option("--source", help="Add source folder", show_default=False),
    ] = None,
    target: Annotated[
        str | None,
        typer.Option("--target", help="Add target folder", show_default=False),
    ] = None,
    profile: Annotated[
        int | None,
        typer.Option(
            "--profile",
            help=(f"profile for copy profile to use, default is {DEFAULT_PROFILE}"),
            show_default=False,
        ),
    ] = None,
    threads: Annotated[
        int,
        typer.Option(
            "--threads",
            help="Number of threads, default is computed automatically",
            show_default=True,
        ),
    ] = DEFAULT_THREADS,
) -> None:
    """The main entry point for the copy command."""
    if ctx.invoked_subcommand is not None:  # pragma: no cover
        return

    if cleanup and merge:
        raise typer.BadParameter("Cannot combine --cleanup with --merge")

    args = CopyArgs(
        dryrun=dryrun,
        all=all_,
        verbosity=verbosity,
        cleanup=cleanup,
        merge=merge,
        skipestimate=skipestimate,
        source=source,
        target=target,
        profile=profile,
        threads=threads,
    )
    run_copy(args)
