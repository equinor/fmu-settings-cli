"""Tests for copy utilities."""

import getpass
import os
import shutil
import time
from pathlib import Path
from typing import Any

import pytest
import typer
from typer.testing import CliRunner

from fmu_settings_cli.__main__ import app
from fmu_settings_cli.copy.copy import (
    DEFAULT_PROFILE,
    DEFAULT_THREADS,
    PROFILE_CUSTOM_FILTER,
    CopyArgs,
    CopyRunner,
    run_copy,
)

TOPLEVELS: list[str] = [
    "r001",
    "r002",
    "20.1.1",
    "19.2.1",
    "32.1.1",
    "something",
    "users",
]

# file structure under folders TOPLEVELS
FILESTRUCTURE: list[str] = [
    "rms/model/workflow.log",
    "rms/input/faults/f1.dat",
    "rms/input/faults/f2.dat",
    "rms/input/faults/f3.dat",
    "rms/output/any_out.dat",
    "rms/output/anyfolder/some_out.dat",
    ".git/some.txt",
    "attic/any.file",
    "backup/whatever.txt",
    "somefolder/any.backup",
    "somefolder/anybackup99.txt",
    "somefolder/attic/any.txt",
    "ert/model/test.ert",
    "ert/model/logs/log.txt",
    "ert/output/log/another_log.txt",
]

runner = CliRunner()
copy_tools_available: bool = all(
    shutil.which(cmd) for cmd in ("rsync", "sh", "bc", "find", "xargs")
)
requires_copy_tools: pytest.MarkDecorator = pytest.mark.skipif(
    not copy_tools_available,
    reason="Copy tests require rsync, sh, bc, find, and xargs",
)


@pytest.fixture
def datatree(tmp_path: Path) -> Path:
    """Create a tmp folder structure for testing."""
    for top in TOPLEVELS:
        top_dir: Path = tmp_path / top
        top_dir.mkdir(parents=True, exist_ok=True)
        (top_dir / "empty").mkdir()
        for file_path in FILESTRUCTURE:
            filepath: Path = top_dir / file_path
            filepath.parent.mkdir(parents=True, exist_ok=True)
            filepath.touch()

    return tmp_path


def test_default_args() -> None:
    """Defaults are populated for copy arguments."""
    args = CopyArgs()
    assert args.profile is None
    assert args.threads == DEFAULT_THREADS


def test_construct_default_target_creates_users_dir(tmp_path: Path) -> None:
    """Default target creation ensures users directory and expected path parts."""
    base: Path = tmp_path / "project"
    base.mkdir()
    source: Path = base / "r1"
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


def test_copy_help() -> None:
    """Help output is available for the copy command."""
    result = runner.invoke(app, ["copy", "--help"])
    assert result.exit_code == 0
    assert "Copy a FMU revision folder" in result.stdout


@requires_copy_tools
def test_rsync_exclude1(datatree: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Testing exclude pattern 1."""
    monkeypatch.chdir(datatree)
    result = runner.invoke(
        app,
        [
            "copy",
            "--source",
            "20.1.1",
            "--profile",
            "1",
            "--target",
            "xxx",
            "--skipestimate",
            "--threads",
            "1",
        ],
    )
    assert result.exit_code == 0
    assert (datatree / "xxx" / "rms" / "model" / "workflow.log").is_file()


def test_construct_target(datatree: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test the construct target routine."""
    monkeypatch.chdir(datatree)
    today: str = time.strftime("%Y%m%d")
    user: str = getpass.getuser()

    runner = CopyRunner(CopyArgs())
    runner.source = "20.1.1"
    runner.construct_target("some_20.1.1")

    assert runner.target == str((datatree / "some_20.1.1").absolute())

    expected: Path = Path("users") / user / "20.1.1" / f"20.1.1_{today}"
    runner.construct_default_target()
    assert runner.default_target == expected


def test_construct_target_shall_fail() -> None:
    """Test the construct target routine with non-existing folder."""
    runner = CopyRunner(CopyArgs())
    runner.source = "nada"
    with pytest.raises(ValueError) as verr:
        runner.construct_default_target()

    assert "Input folder does not exist" in str(verr.value)


@requires_copy_tools
def test_rsync_profile1(datatree: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Testing vs filter profile 1."""
    monkeypatch.chdir(datatree)
    target = "mytest1"
    source = "20.1.1"
    runner = CopyRunner(CopyArgs(threads=1))
    runner.profile = 1
    runner.source = source
    runner.construct_target(target)
    runner.define_filterpattern()
    runner.do_rsyncing()

    assert (datatree / target / "rms" / "input" / "faults" / "f1.dat").exists()
    assert not (datatree / target / "rms" / "input" / "faults" / "x.dat").exists()
    assert (datatree / target / "backup").is_dir()


@requires_copy_tools
def test_rsync_profile3(datatree: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Testing vs filter profile 3."""
    monkeypatch.chdir(datatree)
    target = "mytest3"
    source = "20.1.1"
    runner = CopyRunner(CopyArgs(threads=1))
    runner.profile = 3
    runner.source = source
    runner.construct_target(target)
    runner.define_filterpattern()
    runner.do_rsyncing()

    assert (datatree / target / "rms" / "input" / "faults" / "f1.dat").exists()

    # profile 3: rms/output folders shall be kept but not files
    assert (datatree / target / "rms" / "output").exists()
    assert (datatree / target / "rms" / "output" / "anyfolder").exists()
    assert not (
        datatree / target / "rms" / "output" / "anyfolder" / "some_out.dat"
    ).exists()

    assert not (datatree / target / "rms" / "input" / "faults" / "x.dat").exists()
    assert not (datatree / target / "backup").is_dir()

    assert not (datatree / target / "ert" / "model" / "logs").is_dir()
    assert not (datatree / target / "ert" / "output" / "log").is_dir()


@requires_copy_tools
def test_rsync_profile4(datatree: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Testing vs filter profile 4."""
    monkeypatch.chdir(datatree)
    target = "mytest4"
    source = "20.1.1"
    runner = CopyRunner(CopyArgs(threads=1))
    runner.profile = 4
    runner.source = source
    runner.construct_target(target)
    runner.define_filterpattern()
    runner.do_rsyncing()

    assert (datatree / target / "rms" / "input" / "faults" / "f1.dat").exists()

    # profile 4: rms/output folders will be empty as in option 3 and
    # hence removed according to option 4
    assert not (datatree / target / "rms" / "output").exists()
    assert not (datatree / target / "rms" / "output" / "anyfolder").exists()
    assert not (
        datatree / target / "rms" / "output" / "anyfolder" / "some_out.dat"
    ).exists()

    assert not (datatree / target / "rms" / "input" / "faults" / "x.dat").exists()
    assert not (datatree / target / "backup").is_dir()
    assert (datatree / target / "ert" / "model" / "test.ert").exists()


@requires_copy_tools
@pytest.mark.parametrize(
    "rmsinputperm, profile",
    [
        (0o0400, 1),  # Readable, not executable
        (0o400, 3),
        (0o400, 4),
        (0o100, 1),  # Only executable, not readable
        (0o100, 3),
        (0o100, 4),
        (0o000, 1),  # No permissions
        (0o000, 3),
        (0o000, 4),
    ],
)
@pytest.mark.skipif(
    os.name == "nt", reason="Directory permission semantics differ on Windows"
)
def test_missing_directory_permissions(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    rmsinputperm: int,
    profile: int,
) -> None:
    """Test what happens if one directory is unreadable.

    This situation is only expected as a side effect in rare cases
    and it has only been seen happening on not-interesting directories.
    The important part is to be able to skip the directory with only a
    warning and not a full stop.

    Tests only profiles 1, 3 and 4 which are gives different keepfolders
    values.
    """
    monkeypatch.chdir(tmp_path)
    source = "20.1.1"

    (tmp_path / source / "rms" / "model").mkdir(parents=True)
    (tmp_path / source / "rms" / "input" / "unreachabledir").mkdir(parents=True)
    (tmp_path / source / "rms" / "xx" / "reachabledir").mkdir(parents=True)
    (tmp_path / source / "rms" / "input" / "unreachablefile").touch()

    target = "missing_rms_input"

    try:
        os.chmod(tmp_path / source / "rms" / "input", rmsinputperm)

        (tmp_path / source / "ert").mkdir()
        (tmp_path / source / "ert" / "xcopyme").touch()
        (tmp_path / source / "rms" / "model" / "includeme").touch()
        (tmp_path / source / "rms" / "xx" / "reachabledir" / "a_file").touch()

        result = runner.invoke(
            app,
            [
                "copy",
                "--source",
                source,
                "--target",
                target,
                "--profile",
                str(profile),
                "--skipestimate",
                "--threads",
                "1",
            ],
        )
        assert result.exit_code == 0
        assert (tmp_path / target / "ert" / "xcopyme").exists()
        assert (tmp_path / target / "rms" / "model" / "includeme").exists()
        assert (tmp_path / target / "rms" / "xx" / "reachabledir").exists()
        try:
            assert not (tmp_path / target / "rms" / "input" / "unreachabledir").exists()
            assert not (
                tmp_path / target / "rms" / "input" / "unreachablefile"
            ).exists()
        except PermissionError:
            pass
    finally:
        # Reinstate all user permissions for pytest garbage collection
        os.chmod(tmp_path / source / "rms" / "input", 0o0700)
        target_input = Path(target) / "rms" / "input"
        if target_input.exists():
            # Some of the fmu_copy_revision setups in this test
            # manage to copy the target directory.
            os.chmod(target_input, 0o0700)


@pytest.mark.integration
def test_integration() -> None:
    """Test that the copy command is available."""
    result = runner.invoke(app, ["copy", "--help"])
    assert result.exit_code == 0


@requires_copy_tools
def test_default_profile(datatree: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test command line mode."""
    monkeypatch.chdir(datatree)
    result = runner.invoke(
        app,
        [
            "copy",
            "--source",
            "20.1.1",
            "--skipestimate",
            "--threads",
            "1",
        ],
    )
    assert result.exit_code == 0
    assert f"Doing copy with profile {DEFAULT_PROFILE}" in result.stdout


@requires_copy_tools
def test_choice_profile1(datatree: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test interactive mode, using profile 1."""
    monkeypatch.chdir(datatree)
    profile = 1
    target = "users/jriv/xx1"
    user_input = f"1\n{target}\n{profile}\n"
    result = runner.invoke(
        app,
        ["copy", "--skipestimate", "--threads", "1"],
        input=user_input,
    )

    assert result.exit_code == 0
    assert "Sync files using multiple threads" in result.stdout
    assert target in result.stdout
    assert (datatree / target / "rms" / "input" / "faults" / "f1.dat").exists()
    assert (datatree / target / "rms" / "output" / "any_out.dat").exists()
    assert not (datatree / target / "rms" / "input" / "faults" / "x.dat").exists()
    assert (datatree / target / "backup").is_dir()


@requires_copy_tools
def test_choice_profile3(datatree: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test interactive mode, using profile 3."""
    monkeypatch.chdir(datatree)
    profile = 3
    target = "users/jriv/xx3"
    user_input = f"1\n{target}\n{profile}\n"
    result = runner.invoke(
        app,
        ["copy", "--skipestimate", "--threads", "1"],
        input=user_input,
    )

    assert result.exit_code == 0
    assert "Sync files using multiple threads" in result.stdout
    assert target in result.stdout
    assert (datatree / target / "rms" / "input" / "faults" / "f1.dat").exists()
    assert (datatree / target / "rms" / "output").exists()
    assert not (datatree / target / "rms" / "output" / "any_out.dat").exists()
    assert not (datatree / target / "rms" / "input" / "faults" / "x.dat").exists()
    assert not (datatree / target / "backup").is_dir()


@requires_copy_tools
def test_choice_profile4(datatree: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test interactive mode, using profile 4."""
    monkeypatch.chdir(datatree)
    profile = 4
    target = "users/jriv/xx4"
    user_input = f"1\n{target}\n{profile}\n"
    result = runner.invoke(
        app,
        ["copy", "--skipestimate", "--threads", "1"],
        input=user_input,
    )

    assert result.exit_code == 0
    assert "Sync files using multiple threads" in result.stdout
    assert target in result.stdout
    assert (datatree / target / "rms" / "input" / "faults" / "f1.dat").exists()
    assert not (datatree / target / "rms" / "output").exists()
    assert not (datatree / target / "rms" / "output" / "any_out.dat").exists()
    assert not (datatree / target / "rms" / "input" / "faults" / "x.dat").exists()
    assert not (datatree / target / "backup").is_dir()


@requires_copy_tools
def test_profile_via_args(datatree: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test interactive use but with profile specified on command line."""
    monkeypatch.chdir(datatree)
    target = "users/jriv/xx_cmd_profile"
    user_input = f"1\n{target}\n"
    result = runner.invoke(
        app,
        ["copy", "--profile", "3", "--skipestimate", "--threads", "1"],
        input=user_input,
    )

    assert result.exit_code == 0
    assert "Sync files using multiple threads" in result.stdout
    assert (datatree / target / "rms" / "input" / "faults" / "f1.dat").exists()


@requires_copy_tools
def test_choice_profile3_double_target(
    datatree: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test interactive mode, using profile 3 trying writing to same target twice."""
    monkeypatch.chdir(datatree)
    profile = 3
    target = "users/jriv/xxdouble"
    user_input = f"1\n{target}\n{profile}\n"
    result = runner.invoke(
        app,
        ["copy", "--skipestimate", "--threads", "1"],
        input=user_input,
    )
    assert result.exit_code == 0

    # repeat
    result = runner.invoke(
        app,
        ["copy", "--skipestimate", "--threads", "1"],
        input=user_input,
    )
    assert "So have to exit hard" in result.stderr

    # repeat with cleanup option
    result = runner.invoke(
        app,
        ["copy", "--cleanup", "--skipestimate", "--threads", "1"],
        input=user_input,
    )
    assert result.exit_code == 0
    assert "Doing cleanup of current target" in result.stderr

    # repeat with merge option
    result = runner.invoke(
        app,
        ["copy", "--merge", "--skipestimate", "--threads", "1"],
        input=user_input,
    )
    assert result.exit_code == 0
    assert "Doing merge copy of current target" in result.stderr

    # Combine --cleanup and --merge which shall error
    result = runner.invoke(
        app,
        ["copy", "--cleanup", "--merge"],
        input=user_input,
    )
    assert result.exit_code != 0
    assert "Cannot combine --cleanup with --merge" in result.stderr


@requires_copy_tools
@pytest.mark.parametrize(
    "profile,expected",
    [
        (1, True),
        (2, True),
        (3, True),
        (4, False),
        (5, True),
        (6, False),
    ],
)
def test_profiles_empty_directory_is_copied(
    datatree: Path, monkeypatch: pytest.MonkeyPatch, profile: int, expected: bool
) -> None:
    """Ensure that empty directories are copied as well."""
    monkeypatch.chdir(datatree)
    target = f"users/jriv/xxemptydir{profile}"
    user_input = f"1\n{target}\n{profile}\n"
    result = runner.invoke(
        app,
        ["copy", "--skipestimate", "--threads", "1"],
        input=user_input,
    )
    assert result.exit_code == 0
    empty_dir = Path(target) / "empty"
    assert empty_dir.is_dir() is expected


## Tests below are new (not present in test_fmu_copy_revision.py)


def test_check_folders_all_lists_everything(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Lists all folders when --all is enabled."""
    (tmp_path / "abc").mkdir()
    (tmp_path / "r1").mkdir()
    monkeypatch.chdir(tmp_path)
    runner = CopyRunner(CopyArgs(all=True))
    runner.check_folders()
    assert runner.folders == ["abc", "r1"]


def test_check_folders_no_valid_exits(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Exits when no valid folders exist."""
    (tmp_path / "abc").mkdir()
    monkeypatch.chdir(tmp_path)
    runner = CopyRunner(CopyArgs())
    with pytest.raises(typer.Exit):
        runner.check_folders()


def test_menu_source_folder_rejects_non_numeric(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Rejects non-numeric selection."""
    runner = CopyRunner(CopyArgs())
    runner.folders = ["r1"]
    monkeypatch.setattr("builtins.input", lambda _: "nope")
    with pytest.raises(typer.Exit):
        runner.menu_source_folder()


def test_menu_source_folder_invalid_selection(monkeypatch: pytest.MonkeyPatch) -> None:
    """Rejects out-of-range selection."""
    runner = CopyRunner(CopyArgs())
    runner.folders = ["r1"]
    monkeypatch.setattr("builtins.input", lambda _: "99")
    with pytest.raises(typer.Exit):
        runner.menu_source_folder()


def test_construct_default_target_requires_source() -> None:
    """Constructing default target requires a source."""
    runner = CopyRunner(CopyArgs())
    with pytest.raises(ValueError, match="Source is not set"):
        runner.construct_default_target()


def test_construct_target_requires_source(tmp_path: Path) -> None:
    """Constructing target requires a source."""
    runner = CopyRunner(CopyArgs())
    with pytest.raises(RuntimeError, match="Source is not set"):
        runner.construct_target(tmp_path / "target")


def test_construct_target_same_as_source(tmp_path: Path) -> None:
    """Target cannot be the same as source."""
    source = tmp_path / "source"
    source.mkdir()
    runner = CopyRunner(CopyArgs())
    runner.source = str(source)
    with pytest.raises(RuntimeError, match="same target as source"):
        runner.construct_target(source)


def test_construct_target_cleanup_removes_contents(tmp_path: Path) -> None:
    """Cleanup removes target contents when target exists."""
    source = tmp_path / "source"
    source.mkdir()
    target = tmp_path / "target"
    target.mkdir()
    (target / "file.txt").write_text("data", encoding="utf8")
    (target / "subdir").mkdir()
    (target / "subdir" / "nested.txt").write_text("data", encoding="utf8")

    runner = CopyRunner(CopyArgs(cleanup=True))
    runner.source = str(source)
    runner.construct_target(target)
    assert list(target.iterdir()) == []


def test_menu_target_folder_missing_default_target(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Raises if default target is not constructed."""
    runner = CopyRunner(CopyArgs())

    def _no_default() -> None:
        runner.default_target = None

    monkeypatch.setattr(runner, "construct_default_target", _no_default)
    with pytest.raises(RuntimeError, match="Default target not constructed"):
        runner.menu_target_folder()


def test_check_rms_lockfile_requires_source() -> None:
    """check_rms_lockfile requires a source."""
    runner = CopyRunner(CopyArgs())
    with pytest.raises(RuntimeError, match="Source is not set"):
        runner.check_rms_lockfile()


def test_check_rms_lockfile_stops_on_prompt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Stops when user answers no."""
    source = tmp_path / "src"
    lockfile = source / "rms" / "model" / "proj" / "project_lock_file"
    lockfile.parent.mkdir(parents=True, exist_ok=True)
    lockfile.write_text("lock", encoding="utf8")
    runner = CopyRunner(CopyArgs())
    runner.source = str(source)
    monkeypatch.setattr("fmu_settings_cli.copy.copy.Path.owner", lambda _: "tester")
    monkeypatch.setattr("builtins.input", lambda _: "n")
    with pytest.raises(typer.Exit):
        runner.check_rms_lockfile()


def test_check_rms_lockfile_batch_continues(tmp_path: Path) -> None:
    """Batch mode skips prompt and continues."""
    source = tmp_path / "src"
    lockfile = source / "rms" / "model" / "proj" / "project_lock_file"
    lockfile.parent.mkdir(parents=True, exist_ok=True)
    lockfile.write_text("lock", encoding="utf8")
    runner = CopyRunner(CopyArgs())
    runner.source = str(source)
    runner.batch = True
    runner.check_rms_lockfile()


def test_check_disk_space_requires_source() -> None:
    """check_disk_space requires a source."""
    runner = CopyRunner(CopyArgs())
    with pytest.raises(RuntimeError, match="Source is not set"):
        runner.check_disk_space()


def test_check_disk_space_estimate_and_sleep(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Runs size estimation when skipestimate is False."""
    source = tmp_path / "src"
    source.mkdir()
    (source / "file.txt").write_text("data", encoding="utf8")
    runner = CopyRunner(CopyArgs())
    runner.source = str(source)

    def _disk_usage(_: str | Path) -> tuple[int, int, int]:
        return (10 * 2**30, 0, 10 * 2**30)

    class _FilesystemObject:
        def is_symlink(self) -> bool:
            return False

        def stat(self) -> None:
            raise PermissionError

    monkeypatch.setattr(
        "fmu_settings_cli.copy.copy.Path.rglob",
        lambda *_: [_FilesystemObject()],
    )
    monkeypatch.setattr("fmu_settings_cli.copy.copy.shutil.disk_usage", _disk_usage)
    monkeypatch.setattr("fmu_settings_cli.copy.copy.time.sleep", lambda _: None)
    runner.check_disk_space()


def test_check_disk_space_insufficient_exits(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Exits when not enough space is available."""
    source = tmp_path / "src"
    source.mkdir()
    (source / "big.bin").write_bytes(b"0" * 2048)
    runner = CopyRunner(CopyArgs())
    runner.source = str(source)
    monkeypatch.setattr(
        "fmu_settings_cli.copy.copy.shutil.disk_usage",
        lambda _: (10 * 2**30, 0, 0),
    )
    with pytest.raises(typer.Exit):
        runner.check_disk_space()


def test_show_possible_profiles_custom_filter(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Custom filter profile loads from file."""
    filter_file = tmp_path / "filter.txt"
    filter_file.write_text("filter", encoding="utf8")
    runner = CopyRunner(CopyArgs(profile=PROFILE_CUSTOM_FILTER))
    monkeypatch.setattr("builtins.input", lambda _: str(filter_file))
    runner.show_possible_profiles_copy()
    assert runner.filter == "filter"


def test_do_rsyncing_requires_source_target() -> None:
    """do_rsyncing requires source and target."""
    runner = CopyRunner(CopyArgs())
    with pytest.raises(RuntimeError, match="Source/target not set"):
        runner.do_rsyncing()


def test_do_rsyncing_builds_args_and_threads(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Builds rsync args and computes default thread count."""
    runner = CopyRunner(CopyArgs(dryrun=True, verbosity=True))
    runner.source = str(tmp_path / "src")
    runner.target = str(tmp_path / "dst")
    runner.filter = "+ **"
    runner.dirfilter = "+ */"
    runner.keepfolders = 0

    captured: dict[str, list[str]] = {}

    def _fake_run(
        command: list[str],
        check: bool,
        shell: bool,
        capture_output: bool,
        text: bool,
    ) -> Any:
        captured["command"] = command

        class _Process:
            returncode = 0
            stdout = "line1\nline2\n1.0\n"
            stderr = ""

        return _Process()

    monkeypatch.setattr("fmu_settings_cli.copy.copy.cpu_count", lambda: 2)
    monkeypatch.setattr("fmu_settings_cli.copy.copy.subprocess.run", _fake_run)
    runner.do_rsyncing()

    assert runner.nthreads == 1
    rsyncargs = captured["command"][6]
    assert "--dry-run" in rsyncargs
    assert rsyncargs.count("-v") >= 2  # noqa: PLR2004


def test_run_copy_missing_target_proposal(monkeypatch: pytest.MonkeyPatch) -> None:
    """run_copy raises when target proposal is not set."""

    def _no_default(self: CopyRunner) -> None:
        self.default_target = None

    monkeypatch.setattr(
        "fmu_settings_cli.copy.copy.CopyRunner.construct_default_target",
        _no_default,
    )
    with pytest.raises(RuntimeError, match="Target proposal is not set"):
        run_copy(CopyArgs(source="some-source"))
