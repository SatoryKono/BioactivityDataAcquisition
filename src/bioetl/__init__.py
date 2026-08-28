"""BioETL: Bioactivity data acquisition and processing pipeline."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _pkg_version

__version__ = "6.1.0"

__all__ = ["__version__"]


def get_version() -> str:
    """Return the declared or installed BioETL package version."""
    declared_version = globals().get("__version__")
    try:
        installed_version = _pkg_version("bioetl")
    except PackageNotFoundError:
        installed_version = None

    if isinstance(declared_version, str) and declared_version:
        return declared_version
    return installed_version or "unknown"
