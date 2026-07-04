"""Infrastructure helpers for ``BronzeWriteResult`` file-system checks."""

from __future__ import annotations

from pathlib import Path

from bioetl.domain.value_objects.bronze_result import BronzeWriteResult

__all__ = [
    "is_bronze_write_result_persisted",
]


def is_bronze_write_result_persisted(result: BronzeWriteResult) -> bool:
    """Check whether Bronze output file exists on disk.

    Returns:
        True if the Bronze output file exists at the result's absolute path, False otherwise.
    """
    return Path(result.absolute_path).exists()
