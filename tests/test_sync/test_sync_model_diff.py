"""Tests for the 'fmu sync' model diffing."""

from typing import Any

import pytest
from pydantic import BaseModel

from fmu_settings_cli.sync.model_diff import (
    MAX_LIST_STR_LENGTH,
    MAX_VALUE_STR_LENGTH,
    format_simple_value,
    get_model_diff,
    is_complex_change,
    is_list_of_models,
)

# ruff: noqa: PLR2004


class A(BaseModel):
    """Test model."""

    a: int


class B(BaseModel):
    """Test model."""

    a: int


def test_model_diff_different_models() -> None:
    """Returns if different models."""
    with pytest.raises(ValueError, match="Models must be of the same type"):
        get_model_diff(A(a=0), B(a=0))


@pytest.mark.parametrize(
    "old_val, new_val, expected",
    [
        (A(a=0), None, True),
        (None, A(a=0), True),
        ("foo", A(a=0), True),
        (None, [A(a=0), A(a=0)], True),
        ([A(a=0), A(a=0)], 1, True),
        ([1, 2, 3], None, True),
        (None, [1, 2, 3], True),
        (["a"] * (MAX_LIST_STR_LENGTH + 1), ["a"], True),
        (["supercalifragilisticexpialidocious" * 3], None, True),
        ("foo", "bar", False),
        ([], [], False),
        (3, 4, False),
    ],
)
def test_is_complex_change(old_val: Any, new_val: Any, expected: bool) -> None:
    """Tests that complex changes are correctly found."""
    assert is_complex_change(old_val, new_val) is expected


@pytest.mark.parametrize(
    "value, expected",
    [
        ([A(a=0), {}], False),
        ([], False),
        (3, False),
        (A(a=0), False),
        ([A(a=0), B(a=0)], True),
    ],
)
def test_is_list_of_models(value: Any, expected: bool) -> None:
    """Tests that is_list_of_models detects correctly."""
    assert is_list_of_models(value) is expected


@pytest.mark.parametrize(
    "value, expected",
    [
        (None, "[dim italic]None[/dim italic]"),
        (1, "1"),
        (A(a=0), "A"),
        ("a" * (MAX_VALUE_STR_LENGTH + 1), f"{'a' * MAX_VALUE_STR_LENGTH}..."),
    ],
)
def test_format_simple_value(value: Any, expected: str) -> None:
    """Tests format simple value works as expected."""
    assert format_simple_value(value) == expected
