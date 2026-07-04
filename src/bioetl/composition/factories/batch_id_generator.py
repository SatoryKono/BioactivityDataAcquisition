"""Batch ID generator implementations for composition-layer wiring."""

from __future__ import annotations

from bioetl.composition.occurrence_identity import create_runtime_occurrence_batch_id
from bioetl.domain.types import BatchID


class UuidBatchIdGenerator:
    """Default BatchID generator for operational runtime occurrences."""

    def create(self) -> BatchID:
        """Create a UUID-backed batch identifier without random UUID generation.

        Returns:
            New BatchID wrapping a composition-owned occurrence UUID.
        """
        return create_runtime_occurrence_batch_id("batch_id")


__all__ = ["UuidBatchIdGenerator"]
