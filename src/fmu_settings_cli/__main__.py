"""The main entry point for fmu-settings-cli."""

import argparse
import sys

from fmu_settings_cli import init, settings


def _parse_args(args: list[str] | None = None) -> argparse.Namespace:
    if args is None:
        args = sys.argv[1:]

    parser = argparse.ArgumentParser(
        description="FMU Settings - Manage your FMU project's settings"
    )

    cmd_parser = parser.add_subparsers(dest="command", help="Command to run")

    settings.add_parser(cmd_parser)
    init.add_parser(cmd_parser)

    return parser.parse_args(args)


def main(test_args: list[str] | None = None) -> None:
    """The main entry point."""
    args = _parse_args(test_args)

    match args.command:
        case settings.CMD:
            settings.run(args)
        case init.CMD:
            init.run(args)


if __name__ == "__main__":  # pragma: no cover
    main()
