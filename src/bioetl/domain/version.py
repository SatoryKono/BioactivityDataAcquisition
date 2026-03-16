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
    declared_version: str | None = None
    try:
        from bioetl import __version__ as _declared

        declared_version = _declared
    except ImportError:
        declared_version = None

    try:
        installed_version = _pkg_version("bioetl")
    except PackageNotFoundError:
        installed_version = None

    return declared_version or installed_version or "unknown"
