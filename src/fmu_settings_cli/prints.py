"""Print functions for consistent print styles."""

import sys
from typing import Any

from rich import print


def error(
    *content: Any,
    reason: str | None = None,
    suggestion: str | None = None,
    **kwargs: Any,
) -> None:
    """Prints error messages with optional reason and suggestion.

    Args:
        *content: Any object to print (strings, dict, Rich tables, lists, etc).
        reason: Optional reason/explanation for the error
        suggestion: Optional suggestion or additional info after the reason
        **kwargs: Additional arguments to past to console.print().
    """
    print("[bold red]Error[/bold red]:", *content, **kwargs, file=sys.stderr)

    if reason:
        print(f"  [dim]Reason:[/dim] {reason}", file=sys.stderr)

    if suggestion:
        print(f"  [cyan]→[/cyan] {suggestion}", file=sys.stderr)


def success(
    *content: Any,
    reason: str | None = None,
    suggestion: str | None = None,
    **kwargs: Any,
) -> None:
    """Prints success messages with optional reason and suggestion.

    Args:
        *content: Any object to print (strings, dict, Rich tables, lists, etc).
        reason: Optional reason/explanation for the error
        suggestion: Optional suggestion or additional info after the reason
        **kwargs: Additional arguments to past to console.print().
    """
    print("[bold green]Success[/bold green]:", *content, **kwargs)

    if reason:
        print(f"  [dim]Reason:[/dim] {reason}")

    if suggestion:
        print(f"  [cyan]→[/cyan] {suggestion}")


def info(
    *content: Any,
    reason: str | None = None,
    suggestion: str | None = None,
    **kwargs: Any,
) -> None:
    """Prints info messages with optional reason and suggestion.

    Args:
        *content: Any object to print (strings, dict, Rich tables, lists, etc).
        reason: Optional reason/explanation for the error
        suggestion: Optional suggestion or additional info after the reason
        **kwargs: Additional arguments to past to console.print().
    """
    print("[bold blue]Info[/bold blue]:", *content, **kwargs)

    if reason:
        print(f"  [dim]Reason:[/dim] {reason}")

    if suggestion:
        print(f"  [cyan]→[/cyan] {suggestion}")


def warning(
    *content: Any,
    reason: str | None = None,
    suggestion: str | None = None,
    **kwargs: Any,
) -> None:
    """Prints warning messages with optional reason and suggestion.

    Args:
        *content: Any object to print (strings, dict, Rich tables, lists, etc).
        reason: Optional reason/explanation for the error
        suggestion: Optional suggestion or additional info after the reason
        **kwargs: Additional arguments to past to console.print().
    """
    print("[bold dark_orange]Warning[/bold dark_orange]:", *content, **kwargs)

    if reason:
        print(f"  [dim]Reason:[/dim] {reason}")

    if suggestion:
        print(f"  [cyan]→[/cyan] {suggestion}")
