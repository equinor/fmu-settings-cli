"""Tests for 'rich' print functions."""

from io import StringIO
from unittest.mock import patch

from pydantic import BaseModel, ValidationError

from fmu_settings_cli.prints import (
    error,
    info,
    success,
    validation_error,
    validation_warning,
    warning,
)


class SampleModel(BaseModel):
    """Sample model for testing."""

    name: str
    age: int


def test_success_and_info_print_to_stdout() -> None:
    """Tests that 'success' and 'info' print as expected."""
    with patch("sys.stdout", new=StringIO()) as mock_stdout:
        success("Completed", reason="Passed", suggestion="More")
        info("Foo")

        out = mock_stdout.getvalue()
        assert "Success: Completed" in out
        assert "Reason: Passed" in out
        assert "→ More" in out
        assert "Info: Foo" in out


def test_warning_and_error_print_to_stderr() -> None:
    """Tests that 'warning' and 'error' print as expected."""
    with patch("sys.stderr", new=StringIO()) as mock_stderr:
        warning("Bad", reason="Because")
        error("Failed", suggestion="Fix it")

        err = mock_stderr.getvalue()
        assert "Warning: Bad" in err
        assert "Reason: Because" in err
        assert "Error: Failed" in err
        assert "→ Fix it" in err


def test_validation_error_formats_field_errors() -> None:
    """Tests that validation errors format and print field errors to stderr."""
    with patch("sys.stderr", new=StringIO()) as mock_stderr:
        try:
            SampleModel(name=123, age="invalid")  # type: ignore[arg-type]
        except ValidationError as e:
            validation_error(
                e, message="Invalid data", reason="Type errors", suggestion="Fix types"
            )

        err = mock_stderr.getvalue()
        assert "Error: Invalid data" in err
        assert "Reason: Type errors" in err
        assert "→ name: Input should be a valid string" in err
        assert "→ age: Input should be a valid integer, unable to parse" in err
        assert "→ Fix types" in err


def test_validation_warning_formats_field_errors() -> None:
    """Tests that validation warnings format and print field errors to stderr."""
    with patch("sys.stderr", new=StringIO()) as mock_stderr:
        try:
            SampleModel(name="Drogon", age="invalid")  # type: ignore[arg-type]
        except ValidationError as e:
            validation_warning(e, message="Invalid data")

        err = mock_stderr.getvalue()
        assert "Warning: Invalid data" in err
        assert "→ age: Input should be a valid integer, unable to parse" in err
