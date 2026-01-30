"""Tests for copy core utilities."""

from pathlib import Path

from fmu_settings_cli.copy.copy import (
    DEFAULT_PROFILE,
    DEFAULT_THREADS,
    CopyArgs,
    CopyRunner,
)


def test_default_args() -> None:
    """Defaults are populated for copy arguments."""
    args = CopyArgs()
    assert args.profile is None
    assert args.threads == DEFAULT_THREADS


def test_construct_default_target_creates_users_dir(in_tmp_path: Path) -> None:
    """Default target creation ensures users directory and expected path parts."""
    base = in_tmp_path / "project"
    base.mkdir()
    source = base / "r1"
    source.mkdir()

    args = CopyArgs(source=str(source))
    runner = CopyRunner(args)
    runner.source = str(source)
    runner.construct_default_target()

    assert (base / "users").exists()
    assert runner.default_target is not None
    assert "users" in str(runner.default_target)
    assert "r1" in str(runner.default_target)


def test_define_filterpattern_default_profile() -> None:
    """Default profile sets a non-empty filter."""
    args = CopyArgs()
    runner = CopyRunner(args)
    runner.profile = DEFAULT_PROFILE
    runner.define_filterpattern()
    assert runner.filter
