"""Utility functions for sync'ing."""

from typing import Any, Final

from pydantic import BaseModel
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

MAX_LIST_STR_LENGTH: Final[int] = 50
MAX_VALUE_STR_LENGTH: Final[int] = 30
IGNORED_FIELDS: Final[list[str]] = ["created_at", "created_by"]


def get_model_diff(
    old_model: BaseModel, new_model: BaseModel, prefix: str = ""
) -> list[tuple[str, Any, Any]]:
    """Recursively get differences between two Pydantic models."""
    model_class = type(old_model)
    if type(new_model) is not model_class:
        raise ValueError(
            "Models must be of the same type. Old model is of type "
            f"'{old_model.__class__.__name__}', new model of type "
            f"'{new_model.__class__.__name__}'."
        )

    changes: list[tuple[str, Any, Any]] = []

    for field_name in model_class.model_fields:
        if field_name in IGNORED_FIELDS:
            continue

        old_value = getattr(old_model, field_name)
        new_value = getattr(new_model, field_name)

        field_path = f"{prefix}.{field_name}" if prefix else field_name

        if old_value is None and new_value is not None:
            changes.append((field_path, None, new_value))
        elif old_value is not None and new_value is None:
            changes.append((field_path, old_value, None))
        elif isinstance(old_value, BaseModel) and isinstance(new_value, BaseModel):
            changes.extend(get_model_diff(old_value, new_value, field_path))
        elif isinstance(old_value, list) and isinstance(new_value, list):
            if old_value != new_value:
                changes.append((field_path, old_value, new_value))
        elif old_value != new_value:
            changes.append((field_path, old_value, new_value))

    return changes


def format_simple_value(value: Any, max_length: int = MAX_VALUE_STR_LENGTH) -> str:
    """Format a value for display, handling BaseModels specially."""
    if value is None:
        return "[dim italic]None[/dim italic]"

    if isinstance(value, BaseModel):
        value = type(value).__name__

    str_val = str(value)
    if len(str_val) > max_length:
        return f"{str_val[:max_length]}..."
    return str_val


def is_list_of_models(value: Any) -> bool:
    """Check if value is a list containing BaseModels."""
    return (
        isinstance(value, list)
        and len(value) > 0
        and all(isinstance(v, BaseModel) for v in value)
    )


def is_complex_change(old_val: Any, new_val: Any) -> bool:
    """Determines if a change is complex.

    Complex changes are displayed in a separate table.
    """
    if (
        isinstance(new_val, BaseModel)
        or isinstance(old_val, BaseModel)
        or is_list_of_models(old_val)
        or is_list_of_models(new_val)
    ):
        return True

    # If one of the values is a list
    if isinstance(old_val, list) or isinstance(new_val, list):
        # And the other is None
        if old_val is None or new_val is None:
            return True

        # Or, the string representation is too long
        if (
            len(str(old_val)) > MAX_LIST_STR_LENGTH
            or len(str(new_val)) > MAX_LIST_STR_LENGTH
        ):
            return True

    return False


def add_model_to_panel_content(model: BaseModel, indent: int = 0) -> list[str]:
    """Recursively build panel content line for a BaseModel."""
    lines = []
    indent_str = "  " * indent

    for key, value in model.model_dump().items():
        actual_value = getattr(model, key)

        if isinstance(actual_value, BaseModel):
            lines.append(
                f"{indent_str}[bold]{key}:[/bold] "
                f"[dim]{type(actual_value).__name__}[/dim]"
            )
            lines.extend(add_model_to_panel_content(actual_value, indent + 1))
        elif is_list_of_models(actual_value):
            lines.append(
                f"{indent_str}[bold]{key}:[/bold] [dim]{len(actual_value)} items[/dim]"
            )
            for item in actual_value:
                lines.append(f"{indent_str}  [dim]- {type(item).__name__}[/dim]")
                lines.extend(add_model_to_panel_content(item, indent + 2))
        elif isinstance(value, dict) and not isinstance(actual_value, BaseModel):
            lines.append(f"{indent_str}[bold]{key}:[/bold]")
            for k, v in value.items():
                lines.append(f"{indent_str} [dim]{k}:[/dim] {v}")
        else:
            lines.append(f"{indent_str}[bold]{key}:[/bold] {value}")

    return lines


def render_basemodel_panel(
    model: BaseModel, field_path: str, added: bool = True
) -> Panel:
    """Render a BaseModel as a Rich Panel."""
    content_lines = add_model_to_panel_content(model)
    content = "\n".join(content_lines)
    color = "green" if added else "red"
    action = "Added" if added else "Removed"
    return Panel(
        content,
        title=f"[{color}] {action}: {field_path}[/{color}]",
        border_style=color,
        subtitle=f"[{color}]{type(model).__name__}[/{color}]",
    )


def add_list_to_panel_content(items: list[Any], indent: int = 0) -> list[str]:
    """Build panel content for a list (of models or simple values)."""
    lines = []
    indent_str = "  " * indent

    if is_list_of_models(items):
        for item in items:
            lines.append(f"{indent_str}[dim]- {type(item).__name__}[/dim]")
            lines.extend(add_model_to_panel_content(item, indent + 1))
    else:
        for item in items:
            lines.append(f"{indent_str}[dim]-[/dim] {item}")

    return lines


def render_list_panel(items: list[Any], field_path: str, added: bool = True) -> Panel:
    """Render a list as a rich panel."""
    content_lines = add_list_to_panel_content(items)
    content = "\n".join(content_lines)
    color = "green" if added else "red"
    action = "Added" if added else "Removed"
    return Panel(
        content,
        title=f"[{color}] {action}: {field_path}[/{color}]",
        border_style=color,
        subtitle=f"[{color}]{len(items)} items[/{color}]",
    )


def display_model_diff(
    changes: list[tuple[str, Any, Any]], old_model: BaseModel, new_model: BaseModel
) -> None:
    """Display diff in table format."""
    console = Console()
    if not changes:
        console.print("No changes detected.")
        return

    complex_changes = []

    for field_path, old_val, new_val in changes:
        if is_complex_change(old_val, new_val):
            complex_changes.append((field_path, old_val, new_val))

    table = Table(
        title=f"Value Changes in {type(old_model).__name__}",
        show_header=True,
        header_style="bold",
    )
    table.add_column("Field", style="cyan", no_wrap=True)
    table.add_column("Old Value", style="red")
    table.add_column("New Value", style="green")

    for field_path, old_val, new_val in changes:
        table.add_row(
            field_path, format_simple_value(old_val), format_simple_value(new_val)
        )

    console.print(table)
    console.print()

    if complex_changes:
        table = Table(
            title=f"Complex Changes in {type(old_model).__name__}",
            show_header=True,
            header_style="bold",
        )
        table.add_column("Field", style="cyan", no_wrap=True)
        table.add_column("Change")
        for field_path, old_val, new_val in complex_changes:
            if old_val is None and isinstance(new_val, BaseModel):
                panel = render_basemodel_panel(new_val, field_path, added=True)
                table.add_row(field_path, panel)
            elif isinstance(old_val, BaseModel) and new_val is None:
                panel = render_basemodel_panel(old_val, field_path, added=False)
                table.add_row(field_path, panel)
            elif old_val is None and isinstance(new_val, list):
                panel = render_list_panel(new_val, field_path, added=True)
                table.add_row(field_path, panel)
            elif isinstance(old_val, list) and new_val is None:
                panel = render_list_panel(old_val, field_path, added=False)
                table.add_row(field_path, panel)
            elif isinstance(old_val, list) and isinstance(old_val, list):
                panel_old = render_list_panel(
                    old_val, f"{field_path} (old)", added=False
                )
                table.add_row(field_path, panel_old)
                panel_new = render_list_panel(
                    new_val, f"{field_path} (new)", added=True
                )
                table.add_row(field_path, panel_new)

        console.print(table)

    # Extra new line before prompt
    console.print()
