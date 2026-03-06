"""Infrastructure helpers for ``BronzeWriteResult`` file-system checks."""

from __future__ import annotations

from pathlib import Path
from warnings import warn

from bioetl.domain.value_objects.bronze_result import BronzeWriteResult

__all__ = [
    "bronze_write_result_exists",
    "is_bronze_write_result_persisted",
]


def is_bronze_write_result_persisted(result: BronzeWriteResult) -> bool:
    """Check whether Bronze output file exists on disk.

    Returns:
        True if the Bronze output file exists at the result's absolute path, False otherwise.
    """
    return Path(result.absolute_path).exists()


def bronze_write_result_exists(result: BronzeWriteResult) -> bool:
    """Deprecated compatibility shim for legacy callsites.

    Use ``is_bronze_write_result_persisted`` instead.

    Returns:
        True if the Bronze output file exists at the result's absolute path, False otherwise.
    """
    warn(
        "bronze_write_result_exists() is deprecated; use "
        "is_bronze_write_result_persisted() instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return is_bronze_write_result_persisted(result)
