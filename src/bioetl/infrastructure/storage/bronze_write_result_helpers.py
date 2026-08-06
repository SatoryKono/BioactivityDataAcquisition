"""Infrastructure helpers for ``BronzeWriteResult`` file-system checks."""

from __future__ import annotations

from bioetl.domain.value_objects.bronze_result import BronzeWriteResult
from bioetl.infrastructure.storage.support.path_io import path_exists_bounded

__all__ = [
    "is_bronze_write_result_persisted",
]


def is_bronze_write_result_persisted(result: BronzeWriteResult) -> bool:
    """Check whether Bronze output file exists on disk.

    Uses the storage path-I/O policy (bounded timeout, OSError → False)
    rather than a raw ``Path.exists()`` call.

    Returns:
        True if the Bronze output file exists at the result's absolute path,
        False otherwise (including timeout / I/O failure).
    """
    return path_exists_bounded(result.absolute_path)
