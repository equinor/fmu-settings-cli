"""Print functions for consistent print styles."""

import sys
from typing import Any, Final

from pydantic import ValidationError
from rich import print

_SUCCESS: Final[str] = "[bold green]Success[/bold green]"
_INFO: Final[str] = "[bold blue]Info[/bold blue]"
_ERROR: Final[str] = "[bold red]Error[/bold red]"
_WARNING: Final[str] = "[bold dark_orange]Warning[/bold dark_orange]"
_SUGGESTION: Final[str] = "[bold cyan]→[/bold cyan]"
_REASON: Final[str] = "[bold dim]Reason[/bold dim]"


def _print(
    prefix: str,
    *content: Any,
    reason: str | None = None,
    suggestion: str | None = None,
    **kwargs: Any,
) -> None:
    """Prints error messages with optional reason and suggestion.

    Args:
        prefix: A 'type' indicator prefix for the message, e.g. 'Error', 'Info'.
        *content: Any object to print (strings, dict, Rich tables, lists, etc).
        reason: Optional reason/explanation for the error
        suggestion: Optional suggestion or additional info after the reason.
        **kwargs: Additional arguments to past to console.print().
    """
    print(f"{prefix}:", *content, **kwargs)

    if reason:
        print(f"  {_REASON}: {reason}")

    if suggestion:
        print(f"  {_SUGGESTION} {suggestion}")


def _print_stderr(
    prefix: str,
    *content: Any,
    reason: str | None = None,
    suggestion: str | None = None,
    **kwargs: Any,
) -> None:
    """Prints error messages with optional reason and suggestion.

    Args:
        prefix: A 'type' indicator prefix for the message, e.g. 'Error', 'Info'.
        *content: Any object to print (strings, dict, Rich tables, lists, etc).
        reason: Optional reason/explanation for the error
        suggestion: Optional suggestion or additional info after the reason.
        **kwargs: Additional arguments to past to console.print().
    """
    print(f"{prefix}:", *content, **kwargs, file=sys.stderr)

    if reason:
        print(f"  {_REASON}: {reason}", file=sys.stderr)

    if suggestion:
        print(f"  {_SUGGESTION} {suggestion}", file=sys.stderr)


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
    _print(_SUCCESS, *content, reason=reason, suggestion=suggestion, **kwargs)


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
    _print(_INFO, *content, reason=reason, suggestion=suggestion, **kwargs)


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
    _print_stderr(_WARNING, *content, reason=reason, suggestion=reason, **kwargs)


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
    _print_stderr(_ERROR, *content, reason=reason, suggestion=suggestion, **kwargs)


def validation_error(
    e: ValidationError,
    message: str = "Validation failed",
    reason: str | None = None,
    suggestion: str | None = None,
) -> None:
    """Prints error messages specifically for Pydantic validation errors.

    Args:
        e: ValidationError raised by Pydantic.
        message: General message to present as the error.
        reason: Optional reason/explanation for the error
        suggestion: Optional suggestion or additional info after the reason.
    """
    errors_text = []

    for error in e.errors():
        field = " → ".join(str(loc) for loc in error["loc"])
        msg = error["msg"]
        errors_text.append(f"[yellow]→[/yellow] [bold]{field}[/bold]: {msg}")

    print(f"{_ERROR}:", message, file=sys.stderr)

    if reason:
        print(f"  {_REASON}: {reason}", file=sys.stderr)

    for error_line in errors_text:
        print(f"  {error_line}", file=sys.stderr)

    if suggestion:
        print(f"  {_SUGGESTION} {suggestion}", file=sys.stderr)


def validation_warning(
    e: ValidationError,
    message: str = "Validation failed",
    reason: str | None = None,
    suggestion: str | None = None,
) -> None:
    """Prints warning messages specifically for Pydantic validation errors.

    Args:
        e: ValidationError raised by Pydantic.
        message: General message to present as the error.
        reason: Optional reason/explanation for the error
        suggestion: Optional suggestion or additional info after the reason.
    """
    errors_text = []

    for error in e.errors():
        field = " → ".join(str(loc) for loc in error["loc"])
        msg = error["msg"]
        errors_text.append(f"[bold yellow]→[/bold yellow] [bold]{field}[/bold]: {msg}")

    print(f"{_WARNING}:", message, file=sys.stderr)

    if reason:
        print(f"  {_REASON}: {reason}", file=sys.stderr)

    for error_line in errors_text:
        print(f"  {error_line}", file=sys.stderr)

    if suggestion:
        print(f"  {_SUGGESTION} {suggestion}", file=sys.stderr)
