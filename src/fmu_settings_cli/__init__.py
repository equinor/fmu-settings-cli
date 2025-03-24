"""The fmu.settings.api package."""

try:
    from ._version import __version__, version
except ImportError:
    __version__ = version = "0.0.0"
