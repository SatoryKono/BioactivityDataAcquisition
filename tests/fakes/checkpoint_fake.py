"""In-memory checkpoint implementation for testing.

Implements CheckpointPort interface without filesystem I/O.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from bioetl.domain.types import RunID


class InMemoryCheckpoint:
    """In-memory checkpoint storage for tests.

    Implements CheckpointPort interface from domain/ports.py.
    """

    def __init__(self) -> None:
        """Initialize in-memory checkpoint storage."""
        self._checkpoints: dict[str, tuple[RunID, dict[str, Any]]] = {}

    async def save(
        self,
        pipeline: str,
        run_id: RunID,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Save checkpoint to memory."""
        self._checkpoints[pipeline] = (run_id, metadata or {})

    async def load(self, pipeline: str) -> tuple[RunID, dict[str, Any]] | None:
        """Load checkpoint from memory."""
        return self._checkpoints.get(pipeline)

    async def delete(self, pipeline: str) -> None:
        """Delete checkpoint from memory."""
        self._checkpoints.pop(pipeline, None)

    async def list_all(self) -> list[str]:
        """List all pipelines with checkpoints."""
        return sorted(self._checkpoints.keys())

    async def exists(self, pipeline: str) -> bool:
        """Check if checkpoint exists."""
        return pipeline in self._checkpoints

    async def aclose(self) -> None:
        """Close checkpoint storage (no-op for in-memory)."""
        return None

    def clear(self) -> None:
        """Clear all checkpoints (test utility)."""
        self._checkpoints.clear()
