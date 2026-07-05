"""Local filesystem checkpoint storage.

Implements RULES.md §5.3.1 - Checkpoint Recovery.
"""

from __future__ import annotations

__all__ = ["LocalCheckpointAdapter"]

import asyncio
from pathlib import Path

from bioetl.domain.types import JsonDict, RunID
from bioetl.infrastructure.checkpoint._local_checkpoint_sync import (
    LocalCheckpointSyncMixin,
)


class LocalCheckpointAdapter(LocalCheckpointSyncMixin):
    """Checkpoint storage using local filesystem."""

    def __init__(
        self,
        base_path: str | Path,
        pipeline_name: str | None = None,
    ) -> None:
        """Initialize local checkpoint storage."""
        self.base_path = Path(base_path)
        self.pipeline_name = pipeline_name

    async def save(
        self,
        pipeline: str,
        run_id: RunID,
        metadata: JsonDict | None = None,
    ) -> None:
        """Save checkpoint atomically using temp file + rename."""
        self._save_sync(pipeline, run_id, metadata)

    async def load(self, pipeline: str) -> tuple[RunID, JsonDict] | None:
        """Load the mutable checkpoint pointer for one pipeline."""
        return self._load_sync(pipeline)

    async def delete(self, pipeline: str) -> None:
        """Delete the mutable checkpoint pointer for one pipeline."""
        self._delete_sync(pipeline)

    async def list_all(self) -> list[str]:
        """List all pipelines with mutable checkpoint pointers."""
        return self._list_all_sync()

    async def exists(self, pipeline: str) -> bool:
        """Check if one mutable checkpoint pointer exists."""
        return self._exists_sync(pipeline)

    async def load_for_run(
        self,
        pipeline: str,
        run_id: RunID,
    ) -> tuple[RunID, JsonDict] | None:
        """Load the latest immutable checkpoint evidence stored for one run."""
        return self._load_for_run_sync(pipeline, run_id)

    async def load_for_manifest_id(
        self,
        manifest_id: str,
    ) -> tuple[RunID, JsonDict] | None:
        """Load immutable checkpoint evidence indexed by manifest identity."""
        return self._load_for_manifest_id_sync(manifest_id)

    async def load_latest_for_pipeline(
        self,
        pipeline: str,
    ) -> tuple[RunID, JsonDict] | None:
        """Load latest immutable checkpoint evidence across all runs for one pipeline."""
        return self._load_latest_for_pipeline_sync(pipeline)

    async def aclose(self) -> None:
        """Close checkpoint storage (no-op for local filesystem)."""
        await asyncio.sleep(0)
