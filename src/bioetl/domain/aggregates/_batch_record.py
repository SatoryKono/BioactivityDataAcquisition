"""Batch record value object.

Contains the frozen BatchRecord dataclass for records within a Batch.
"""

from __future__ import annotations

from dataclasses import dataclass

from bioetl.domain.types import (
    BronzeRecord,
    ContentHash,
    EntityID,
)

__all__ = [
    "BatchRecord",
]


@dataclass(frozen=True, slots=True)
class BatchRecord:
    """Immutable value object representing a record in a batch.

    Attributes:
        index: Sequential index within the batch.
        entity_id: Business key for the entity.
        content_hash: SHA256 hash for versioning.
        data: The actual record data.
        is_valid: Whether the record passed validation.
        error: Error message if validation failed.
        error_code: Error classification code.
    """

    index: int
    entity_id: EntityID | None
    content_hash: ContentHash | None
    data: BronzeRecord
    is_valid: bool = True
    error: str | None = None
    error_code: str | None = None

    def __post_init__(self) -> None:
        """Validate record invariants."""
        if self.index < 0:
            raise ValueError(f"Record index cannot be negative: {self.index}")
        if not self.is_valid and not self.error:
            raise ValueError("Invalid record must have an error message")

    def with_validation_error(
        self, error: str, error_code: str | None = None
    ) -> BatchRecord:
        """Create a new BatchRecord marked as invalid.

        Args:
            error: Error message.
            error_code: Error classification.

        Returns:
            New BatchRecord with is_valid=False.
        """
        return BatchRecord(
            index=self.index,
            entity_id=self.entity_id,
            content_hash=self.content_hash,
            data=self.data,
            is_valid=False,
            error=error,
            error_code=error_code,
        )
