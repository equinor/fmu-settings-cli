"""Root configuration for pytest."""

import argparse
import sys
from unittest.mock import patch

import pytest

from fmu_settings_cli.__main__ import _parse_args


@pytest.fixture
def default_args() -> argparse.Namespace:
    """Returns default arguments when running `fmu-settings`."""
    with patch.object(sys, "argv", ["fmu-settings"]):
        return _parse_args()
