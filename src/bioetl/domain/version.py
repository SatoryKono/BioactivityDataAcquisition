"""BioETL version utilities."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _pkg_version

__all__ = ["get_version"]


def get_version() -> str:
    """Get BioETL package version.

    Returns:
        Version string or 'unknown' if package is not installed.
    """
    try:
        return _pkg_version("bioetl")
    except PackageNotFoundError:
        try:
            from bioetl import __version__ as _fallback

            return _fallback
        except ImportError:
            return "unknown"
