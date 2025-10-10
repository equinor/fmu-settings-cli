"""Root configuration for pytest."""

import argparse
import sys
from collections.abc import Generator
from unittest.mock import patch

import pytest

from fmu_settings_cli.__main__ import _parse_args


@pytest.fixture
def default_args() -> argparse.Namespace:
    """Returns default arguments when running `fmu-settings`."""
    with patch.object(sys, "argv", ["fmu", "settings"]):
        return _parse_args()


@pytest.fixture
def patch_ensure_port() -> Generator[None]:
    """Patches ensure port so tests can run if fmu-settings is running."""
    with patch("fmu_settings_cli.settings.main.ensure_port"):
        yield
