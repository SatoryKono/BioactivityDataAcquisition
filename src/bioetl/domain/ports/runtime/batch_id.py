"""Port for batch identifier generation.

Allows deterministic batch IDs in tests via dependency injection.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from bioetl.domain.types import BatchID


@runtime_checkable
class BatchIdGeneratorPort(Protocol):
    """Factory contract for creating batch identifiers."""

    def create(self) -> BatchID:
        """Create a new batch identifier."""
        ...


__all__ = ["BatchIdGeneratorPort"]
