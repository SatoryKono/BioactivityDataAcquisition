"""Local filesystem checkpoint storage.

Implements RULES.md §5.3.1 - Checkpoint Recovery.

Requirements:
- REQ-CHECKPOINT-001: Check existence on startup
- REQ-CHECKPOINT-002: Atomic writes (temp file + rename)
- REQ-CHECKPOINT-003: Recovery on --resume flag
- REQ-CHECKPOINT-004: Delete after successful run

Architecture:
- Stores checkpoints as JSON on local filesystem
- Path: {base_path}/{provider}_{entity}.json (flat structure)
- Atomic writes via temp file + os.replace
- Metadata includes run_id and custom metadata
"""

from __future__ import annotations

__all__ = ["LocalCheckpoint"]


import asyncio
import os
import tempfile
from pathlib import Path
from uuid import UUID

from bioetl.domain.serialization import deserialize_from_json, serialize_to_json
from bioetl.domain.types import JsonDict, RunID


class LocalCheckpoint:
    """Checkpoint storage using local filesystem.

    Implements CheckpointPort interface from domain/ports.py.
    """

    def __init__(
        self,
        base_path: str | Path,
        pipeline_name: str | None = None,
    ) -> None:
        """Initialize local checkpoint storage.

        Args:
            base_path: Base path for checkpoint storage
            pipeline_name: Optional pipeline name (for interface compatibility)

        """
        self.base_path = Path(base_path)
        self.pipeline_name = pipeline_name

    async def save(
        self,
        pipeline: str,
        run_id: RunID,
        metadata: JsonDict  # Any: checkpoint state has heterogeneous values
        | None = None,  # Any: checkpoint metadata values are heterogeneous
    ) -> None:
        """Save checkpoint atomically using temp file + rename.

        Uses run_in_executor to avoid blocking the event loop.

        Args:
            pipeline: Pipeline.
            run_id: Pipeline run identifier.
            metadata: Associated metadata.
        """
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self._save_sync, pipeline, run_id, metadata)

    def _save_sync(
        self,
        pipeline: str,
        run_id: RunID,
        metadata: JsonDict  # Any: checkpoint state has heterogeneous values
        | None,  # Any: checkpoint metadata values are heterogeneous
    ) -> None:
        """Synchronous save implementation."""
        key = self._get_key(pipeline)
        full_path = self.base_path / key
        full_path.parent.mkdir(parents=True, exist_ok=True)

        checkpoint_data = {
            "pipeline": pipeline,
            "run_id": str(run_id),
            "metadata": metadata or {},
            "version": "2.0",
        }
        checkpoint_json = serialize_to_json(checkpoint_data, ensure_ascii=False)

        # Atomic write: write to temp file, then replace
        fd, temp_path = tempfile.mkstemp(
            dir=full_path.parent,
            prefix=".checkpoint_",
            suffix=".tmp",
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(checkpoint_json)
            # Use Path.replace for cross-platform atomic overwrite
            Path(temp_path).replace(full_path)
        except (OSError, ValueError, TypeError, RuntimeError):
            # Clean up temp file on error
            temp_file = Path(temp_path)
            if temp_file.exists():
                temp_file.unlink()
            raise

    async def load(
        self, pipeline: str
    ) -> (
        tuple[RunID, JsonDict]  # Any: checkpoint state has heterogeneous values
        | None  # Any: checkpoint state has heterogeneous values
    ):  # Any: checkpoint state has heterogeneous values
        """Load last checkpoint.

        Uses run_in_executor to avoid blocking the event loop.

        Args:
            pipeline: Pipeline.

        Returns:
            Loaded tuple[RunID, JsonDict] | None.
        """
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._load_sync, pipeline)

    def _load_sync(
        self, pipeline: str
    ) -> (
        tuple[RunID, JsonDict]  # Any: checkpoint state has heterogeneous values
        | None  # Any: checkpoint state has heterogeneous values
    ):  # Any: checkpoint state has heterogeneous values
        """Synchronous load implementation.

        Returns:
            Tuple of (RunID, metadata dict) if checkpoint exists, None otherwise.
        """
        key = self._get_key(pipeline)
        full_path = self.base_path / key

        if not full_path.exists():
            return None

        with open(full_path, encoding="utf-8") as f:
            checkpoint_json = f.read()

        checkpoint_data = deserialize_from_json(checkpoint_json)
        if not isinstance(checkpoint_data, dict):
            raise ValueError("Checkpoint data must be a dictionary")
        run_id = RunID(UUID(checkpoint_data["run_id"]))
        metadata = checkpoint_data.get("metadata", {})
        return (run_id, metadata)

    async def delete(self, pipeline: str) -> None:
        """Delete checkpoint.

        Uses run_in_executor to avoid blocking the event loop.

        Args:
            pipeline: Pipeline.
        """
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self._delete_sync, pipeline)

    def _delete_sync(self, pipeline: str) -> None:
        """Synchronous delete implementation."""
        key = self._get_key(pipeline)
        full_path = self.base_path / key

        if full_path.exists():
            full_path.unlink()

    async def list_all(self) -> list[str]:
        """List all pipelines with checkpoints.

        Uses run_in_executor to avoid blocking the event loop.

        Returns:
            Collection of all.
        """
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._list_all_sync)

    def _list_all_sync(self) -> list[str]:
        """Synchronous list_all implementation.

        Lists all pipelines with checkpoints by scanning for .json files
        directly in the base path (flat structure).

        Returns:
            Sorted list of pipeline name strings with existing checkpoint files.
        """
        pipelines: set[str] = set()

        if self.base_path.exists():
            for path in self.base_path.iterdir():
                if path.is_file() and path.suffix == ".json":
                    # Remove .json suffix to get pipeline name
                    pipelines.add(path.stem)

        return sorted(pipelines)

    async def exists(self, pipeline: str) -> bool:
        """Check if checkpoint exists.

        Uses run_in_executor to avoid blocking the event loop.

        Args:
            pipeline: Pipeline.

        Returns:
            True if condition is met, False otherwise.
        """
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._exists_sync, pipeline)

    def _exists_sync(self, pipeline: str) -> bool:
        """Synchronous exists implementation.

        Returns:
            True if the checkpoint file for the given pipeline exists, False otherwise.
        """
        key = self._get_key(pipeline)
        return (self.base_path / key).exists()

    def _get_key(self, pipeline: str) -> str:
        """Get checkpoint file path for a pipeline.

        Returns flat path: {pipeline}.json (e.g., chembl_activity.json)
        The base_path already points to data/output/checkpoints/.

        Returns:
            Filename string for the checkpoint file (e.g., 'chembl_activity.json').
        """
        return f"{pipeline}.json"

    async def aclose(self) -> None:
        """Close checkpoint storage (no-op for local filesystem)."""
