"""In-memory checkpoint implementation for testing.

Implements CheckpointPort interface without filesystem I/O.
"""

from __future__ import annotations

import asyncio
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
        await asyncio.sleep(0)
        self._checkpoints[pipeline] = (run_id, metadata or {})

    async def load(self, pipeline: str) -> tuple[RunID, dict[str, Any]] | None:
        """Load checkpoint from memory."""
        await asyncio.sleep(0)
        return self._checkpoints.get(pipeline)

    async def delete(self, pipeline: str) -> None:
        """Delete checkpoint from memory."""
        await asyncio.sleep(0)
        self._checkpoints.pop(pipeline, None)

    async def list_all(self) -> list[str]:
        """List all pipelines with checkpoints."""
        await asyncio.sleep(0)
        return sorted(self._checkpoints.keys())

    async def exists(self, pipeline: str) -> bool:
        """Check if checkpoint exists."""
        await asyncio.sleep(0)
        return pipeline in self._checkpoints

    async def aclose(self) -> None:
        """Close checkpoint storage (no-op for in-memory)."""
        await asyncio.sleep(0)

    def clear(self) -> None:
        """Clear all checkpoints (test utility)."""
        self._checkpoints.clear()
