"""Copy logic ported from fmu_copy_revision."""

from __future__ import annotations

import getpass
import shlex
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass
from multiprocessing import cpu_count
from os.path import join
from pathlib import Path

import typer

from fmu_settings_cli.prints import error, info, warning

DESCRIPTION = """This is a simple interactive script for copying a FMU revision folder
with features:

    1. Selective copy, i.e. avoid data that can be regenerated
    2. Speed up copying by multithreading
    3. Retain correct file dates and user permissions

Usage:

    fmu copy  (for menu based input)

    or

    fmu copy --source 21.0.0 --target some --profile 3 --threads 6 --cleanup
    or

    fmu copy --source 21.0.0  (...other options are defaulted)
"""

USERMENU = """\

By default some file types and directories will be skipped. Here are some profiles:

1. Copy everything

2. Copy everything, except:
    * Directories with name 'backup'
    * Directories with name 'users'
    * Directories with name 'attic'
    * Directories and files with names or extension '.git' or '.svn'
    * Files ending with ~
    * Empty folders (except those listed above) will be kept

3. Copy everything, except:
    * All folders and files mentioned in option 2
    * The following folders under ert/ (if they exist):
        - 'output'
        - 'ert/*/storage', including 'ert/storage' (for backw compat.)
    * The following folders or files under rms/ (if they exist):
        - 'input/seismic', 'model/*.log'
    * The following files under rms/ (if they exist):
        - All files under 'output' folders (folders will be kept!)
    * The following files and folders under spotfire/:
        - 'input/*.csv', 'input/*/.csv' 'model/*.dxp', 'model/*/*.dxp'
    * The following folders under share/:
        - 'results'
        - 'templates'
    * Empty folders (at destination) except those listed above will kept

4. As profile 3, but also all empty folder (at destination) will removed.
    This the DEFAULT profile!

5. As profile 3, but keeps more data:
    * Folders and files rms/output will be kept
    * Folders and files share/results and share/templates will be kept.

6. Only copy the <coviz> folder (if present), which shall be under
    <revision>/share/coviz:
    * Symbolic links will be kept, if possible

9. Make your own filter rules in a named file. For syntax, see e.g.
    https://linux.die.net/man/1/rsync
"""

DEFAULT_PROFILE = 4
DEFAULT_THREADS = 99
PROFILE_CUSTOM_FILTER = 9
FILESIZE_BASE = 1024
PROFILE_COPY_ALL = 1
PROFILE_COPY_EXCLUDE_COMMON = 2
PROFILE_COPY_EXCLUDE_EXTENDED = 3
PROFILE_COPY_EXCLUDE_EMPTY = 4
PROFILE_COPY_KEEP_MORE = 5
PROFILE_COPY_COVIZ_ONLY = 6

FILTER1 = """
+ **
"""

FILTER2 = """
- backup/**
- users/**
- attic/**
- .git/**
- *.git
- *.svn
- *~
"""

DIRFILTER2 = """
- backup/
- users/
- attic/
- .git/
+ */
- *
"""

FILTER3_ADD = """
- ert/output/**
- ert/storage/**
- ert/output/storage/**
- ert/model/logs/**
- ert/output/log/**
- input/seismic/**
- rms/model/*.log
- rms/output/**
- spotfire/**/*.csv
- spotfire/**/*.dxp
- share/results/**
- share/templates/**
"""

FILTER3 = FILTER2 + FILTER3_ADD

DIRFILTER3 = """
- backup/
- users/
- attic/
- .git/
- ert/output/
- ert/storage/
- ert/**/storage/
- ert/model/logs/
- rms/input/seismic/
- share/results/
- share/templates/
+ */
- *
"""

FILTER5_ADD = """
+ rms/output/**
+ share/results/**
+ share/templates/**
"""

FILTER5 = FILTER2 + FILTER5_ADD + FILTER3_ADD

DIRFILTER5 = """
- backup/
- users/
- attic/
- .git/
- ert/output/
- ert/storage/
- ert/**/storage/
- rms/input/seismic/
+ */
- *
"""

DIRFILTERX = """
+ */
- *
"""

FILTER6 = """
+ share/coviz/**
- *
"""

SHELLSCRIPT = """\
#!/usr/bin/sh

# SETUP OPTIONS

SRCDIR="$1"  # a relative path
DESTDIR="$2"  # must be an absolute path!
FILTERFILE="$3"
THREADS=$4
RSYNCARGS="$5"
KEEPFOLDERS=$6  # if 1 first copy folder tree, if 2 do it afterwards with dirfilterfile
DIRFILTERFILE="$7"

PWD=$(pwd)

start=`date +%s.%N`

cd $SRCDIR

echo " ** Target folder is $DESTDIR"
mkdir -p $DESTDIR

echo " ** Sync folders and files!"

if [ $KEEPFOLDERS -eq 1 ]; then
    echo " ** Sync all folders first... ($KEEPFOLDERS)"  # this is usually fast
    rsync -a -f"+ */" -f"- *" . $DESTDIR
fi

echo " ** Sync files using multiple threads..."
find -L . -type f | xargs -n1 -P$THREADS -I% \
    rsync $RSYNCARGS -f"merge $FILTERFILE" % $DESTDIR

if [ $KEEPFOLDERS -eq 2 ]; then
    echo " ** Sync all folders (also empty) except some... ($KEEPFOLDERS)"
    rsync -a -f"merge $DIRFILTERFILE" . $DESTDIR
fi

end=`date +%s.%N`

runtime=$( echo "$end - $start" | bc -l )

echo " ** Compute runtime..."
echo $runtime
cd $PWD

"""


@dataclass(frozen=True)
class CopyArgs:
    """Arguments for a copy run."""

    dryrun: bool = False
    all: bool = False
    verbosity: bool = False
    cleanup: bool = False
    merge: bool = False
    skipestimate: bool = False
    source: str | None = None
    target: str | None = None
    profile: int | None = None
    threads: int = DEFAULT_THREADS


class CopyRunner:
    """Runner for copying a FMU revision."""

    def __init__(self, args: CopyArgs) -> None:
        """Initialize the copy runner."""
        self.args: CopyArgs = args
        self.folders: list[str] = []
        self.source: str | None = None
        self.default_target: Path | None = None
        self.target: str | None = None
        self.nthreads: int | None = None
        self.profile: int | None = None
        self.filter: str = ""
        self.dirfilter: str = ""
        self.batch = False
        self.keepfolders = 0

    def check_folders(self) -> None:
        """Check if potential fmu folders are present or list all if --all."""
        current = Path(".")
        folders = [file for file in current.iterdir() if file.is_dir()]
        result = []
        for folder in folders:
            fname = folder.name
            if not self.args.all:
                if fname.startswith(("r", "1", "2", "3")):
                    result.append(fname)
            else:
                result.append(fname)

        if result:
            result = sorted(result)

        if not result:
            error(
                "No valid folders to list. Are you in the correct folder "
                "above your revisions? Or consider --all option to list all folders."
            )
            raise typer.Exit(code=1)

        self.folders = result

    def menu_source_folder(self) -> None:
        """Print an interactive menu to the user for which folder."""
        info("Choices:\n")

        default = 0
        for inum, res in enumerate(self.folders):
            info(f"{inum + 1:4d}:  {res}")
            default = inum + 1
        try:
            select = int(input(f"\nChoose number, default is {default}: ") or default)
        except ValueError as err:
            error("Selection is not a number")
            raise typer.Exit(code=1) from err

        if select in range(1, len(self.folders) + 1):
            usefolder = self.folders[select - 1]
            info(f"Selection <{select}> seems valid, folder to use is <{usefolder}>")
        else:
            error("Invalid selection!")
            raise typer.Exit(code=1)

        self.source = usefolder

    def construct_default_target(self) -> None:
        """Validate source and construct default target from source path."""
        if self.source is None:
            raise ValueError("Source is not set")

        sourcepath = Path(self.source)
        sourcenode = sourcepath.name

        if not sourcepath.exists():
            raise ValueError("Input folder does not exist!")

        today = time.strftime("%Y%m%d")
        user = getpass.getuser()

        userpath = sourcepath.parent / "users"
        if not userpath.exists():
            userpath.mkdir(parents=False, exist_ok=True)

        xsource = sourcenode + "_" + today
        self.default_target = Path(userpath) / user / sourcenode / xsource

    def construct_target(self, proposal: str | Path) -> None:
        """Final target as abs path string, and evaluate cleanup or merge."""

        def _clean_folder(folder: str) -> None:
            for item in Path(folder).iterdir():
                if item.is_dir():
                    shutil.rmtree(item)
                else:
                    item.unlink()

        target = Path(proposal)
        self.target = str(target.absolute())
        info(f"Selected target is <{self.target}>")

        if self.source is None:
            raise RuntimeError("Source is not set")

        if self.target == str(Path(self.source).absolute()):
            raise RuntimeError("You cannot have same target as source!")

        if target.is_dir():
            warning(f"Target is already present: <{self.target}>")
            if self.args.cleanup:
                warning("Doing cleanup of current target...")
                _clean_folder(self.target)

            elif self.args.merge:
                warning("Doing merge copy of current target...")
            else:
                error(
                    "Current target exists but neither --cleanup or --merge is "
                    "applied on command line. So have to exit hard!\nSTOP!\n"
                )
                raise typer.Exit(code=1)

    def menu_target_folder(self) -> None:
        """Print an interactive menu to the user for target."""
        self.construct_default_target()
        if self.default_target is None:
            raise RuntimeError("Default target not constructed")
        dft = self.default_target
        propose = input(f"Choose output folder (default is <{dft}>: ") or dft
        self.construct_target(propose)

    def check_rms_lockfile(self) -> None:
        """Check if RMS project has an active lockfile if interactive mode."""
        if self.source is None:
            raise RuntimeError("Source is not set")

        lockfiles = list(Path(self.source).glob("rms/model/*/project_lock_file"))

        if lockfiles:
            warning(
                "Warning, it seems that one or more RMS projects have a lock file "
                "and may perhaps be in a saving process..."
            )
            for lockfile in lockfiles:
                warning(f"<{lockfile}> owner of lockfile is {lockfile.owner()}")

            if not self.batch:
                answer = (
                    input("Continue anyway? (default is 'Yes' if you press enter): ")
                    or "Y"
                )
                if not answer.startswith(("y", "Y")):
                    warning("Stopped by user")
                    raise typer.Exit(code=1)

            warning("Will continue...")

    def check_disk_space(self) -> None:
        """Checking diskspace."""
        if self.source is None:
            raise RuntimeError("Source is not set")

        info("Checking disk space at current partition...")
        total, used, free = shutil.disk_usage(".")
        info(f"  Total: {total // (2**30):d} G")
        info(f"  Used:  {used // (2**30):d} G")
        info(f"  Free:  {free // (2**30):d} G")

        if self.args.skipestimate:
            info("  Skip estimation of current revision size!")
            return

        info(f"  Estimate size of current revision <{self.source}> ...")

        freekbytes = free // 1024

        def _get_size(path: str) -> int:
            disksum = 0
            for filesystemobject in Path(path).rglob("*"):
                try:
                    if not filesystemobject.is_symlink():
                        disksum += filesystemobject.stat().st_size
                except PermissionError:
                    warning(
                        f"Could not get size of {filesystemobject}, Permission denied"
                    )
            return disksum

        def _filesize(size: float) -> str:
            for unit in ("B", "K", "M", "G"):  # noqa: B007
                if size < FILESIZE_BASE:
                    break
                size /= FILESIZE_BASE
            return f"{size:.1f} {unit}"

        fsize = _get_size(self.source)
        info(f"\n  Size of existing revision is: {_filesize(fsize)}\n")

        sourcekbytes = fsize // 1024
        if sourcekbytes > freekbytes:
            error("Not enough space left for copying! STOP!")
            raise typer.Exit(code=1)

        time.sleep(1)

    def show_possible_profiles_copy(self) -> None:
        """Show a menu for possible profiles for copy/rsync."""
        if self.args.profile is None:
            info(USERMENU)
            self.profile = int(
                input(f"Choose (default is {DEFAULT_PROFILE}): ") or DEFAULT_PROFILE
            )
        else:
            self.profile = int(self.args.profile)

        if self.profile == PROFILE_CUSTOM_FILTER:
            ffile = input("Choose rsync filter file: ")
            with open(ffile, encoding="utf8") as stream:
                self.filter = stream.read()

    def define_filterpattern(self) -> None:
        """Define filterpattern pattern based on menu choice or command line input."""
        filterpattern = ""
        dirfilterpattern = ""
        self.keepfolders = 0

        if self.profile == PROFILE_COPY_ALL:
            filterpattern = FILTER1
            self.keepfolders = 1
            dirfilterpattern = DIRFILTERX
        elif self.profile == PROFILE_COPY_EXCLUDE_COMMON:
            filterpattern = FILTER2
            self.keepfolders = 2
            dirfilterpattern = DIRFILTER2
        elif self.profile == PROFILE_COPY_EXCLUDE_EXTENDED:
            filterpattern = FILTER3
            self.keepfolders = 2
            dirfilterpattern = DIRFILTER3
        elif self.profile == PROFILE_COPY_EXCLUDE_EMPTY:
            filterpattern = FILTER3
            self.keepfolders = 0
            dirfilterpattern = DIRFILTERX
        elif self.profile == PROFILE_COPY_KEEP_MORE:
            filterpattern = FILTER5
            self.keepfolders = 2
            dirfilterpattern = DIRFILTER5
        elif self.profile == PROFILE_COPY_COVIZ_ONLY:
            filterpattern = FILTER6
            self.keepfolders = 0
            dirfilterpattern = DIRFILTERX

        if self.profile != PROFILE_CUSTOM_FILTER:
            self.filter = filterpattern
            self.dirfilter = dirfilterpattern

    def do_rsyncing(self) -> None:
        """Do the actual rsync job using a shell script made temporary."""
        if self.source is None or self.target is None:
            raise RuntimeError("Source/target not set")

        with tempfile.TemporaryDirectory() as tdir:
            scriptname = join(tdir, "rsync.sh")
            filterpatternname = join(tdir, "filterpattern.txt")
            dirfilterpatternname = join(tdir, "dirfilterpattern.txt")

            Path(scriptname).write_text(SHELLSCRIPT, encoding="utf8")
            Path(filterpatternname).write_text(self.filter, encoding="utf8")
            Path(dirfilterpatternname).write_text(self.dirfilter, encoding="utf8")

            self.nthreads = self.args.threads
            if self.nthreads == DEFAULT_THREADS:
                self.nthreads = cpu_count() - 1 if cpu_count() > 1 else 1

            info(
                f"Doing copy with profile {self.profile} "
                f"using {self.nthreads} CPU threads, please wait..."
            )

            rsyncargs = ["-a", "-R", "--delete"]

            if self.args.dryrun:
                rsyncargs.extend(["--dry-run", "-v"])

            if self.args.verbosity:
                rsyncargs.append("-v")

            rsyncargs_str = shlex.join(rsyncargs)

            command = [
                "sh",
                scriptname,
                self.source,
                self.target,
                filterpatternname,
                str(self.nthreads),
                rsyncargs_str,
                str(self.keepfolders),
                dirfilterpatternname,
            ]

            process = subprocess.run(
                command,
                check=True,
                shell=False,
                capture_output=True,
                text=True,
            )
            stdout = process.stdout.splitlines()
            stderr = process.stderr.splitlines()

            info("\n".join(stdout[:-2]))

            if process.returncode != 0 or stderr:
                warning("\n".join(stderr))

            timing_seconds = float(stdout[-1])
            timing = time.strftime(
                "%H hours %M minutes %S seconds", time.gmtime(timing_seconds)
            )
            info(
                "\n ** The rsync process took "
                f"{timing}, using {self.nthreads} threads **\n"
            )


def _resolve_profile(args: CopyArgs) -> int:
    return int(args.profile or DEFAULT_PROFILE)


def run_copy(args: CopyArgs) -> None:
    """Entry point to run copy interactively or in batch mode."""
    runner = CopyRunner(args)

    if not args.source:
        runner.check_folders()
        runner.menu_source_folder()
        runner.menu_target_folder()
        runner.check_rms_lockfile()
        runner.check_disk_space()
        runner.show_possible_profiles_copy()
        runner.define_filterpattern()
        runner.do_rsyncing()
    else:
        info("Command line mode!")
        runner.profile = _resolve_profile(args)
        runner.source = args.source
        runner.batch = True

        if not args.target:
            runner.construct_default_target()
            proposal = runner.default_target
        else:
            proposal = Path(args.target)
        if proposal is None:
            raise RuntimeError("Target proposal is not set")
        runner.construct_target(proposal)
        runner.check_disk_space()
        runner.define_filterpattern()
        info(
            f"Using source <{runner.source}>, target <{runner.target}> with "
            f"profile <{runner.profile}> ..."
        )
        runner.do_rsyncing()
