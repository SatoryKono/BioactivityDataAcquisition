"""Batch ID generator implementations for composition-layer wiring."""

from __future__ import annotations

from uuid import uuid4

from bioetl.domain.types import BatchID


class UuidBatchIdGenerator:
    """Default batch ID generator based on ``uuid4``."""

    def create(self) -> BatchID:
        """Create a UUID-backed batch identifier.

        Returns:
            New BatchID wrapping a freshly generated UUID4.
        """
        return BatchID(uuid4())


__all__ = ["UuidBatchIdGenerator"]
