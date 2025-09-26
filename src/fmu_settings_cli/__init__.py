"""The fmu.settings.api package."""

try:
    from ._version import __version__, version
except ImportError:  # pragma: no cover
    __version__ = version = "0.0.0"
