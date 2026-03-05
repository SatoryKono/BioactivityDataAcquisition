"""Batch status enum.

Contains the BatchStatus StrEnum for batch lifecycle states.
"""

from __future__ import annotations

from enum import StrEnum

__all__ = [
    "BatchStatus",
]


class BatchStatus(StrEnum):
    """Status of a batch."""

    OPEN = "open"
    """Batch is accepting new records."""

    SEALED = "sealed"
    """Batch is sealed, no more records can be added."""

    WRITING = "writing"
    """Batch is being written to storage."""

    COMMITTED = "committed"
    """Batch has been successfully written."""

    FAILED = "failed"
    """Batch write failed."""

    def is_modifiable(self) -> bool:
        """Check if records can still be added.

        Returns:
            True if the condition is met, False otherwise.
        """
        return self == BatchStatus.OPEN
