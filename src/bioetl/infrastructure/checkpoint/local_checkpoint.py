"""Local filesystem checkpoint storage.

Implements RULES.md §5.3.1 - Checkpoint Recovery.

Requirements:
- REQ-CHECKPOINT-001: Check existence on startup
- REQ-CHECKPOINT-002: Atomic writes (temp file + rename)
- REQ-CHECKPOINT-003: Recovery on --resume flag
- REQ-CHECKPOINT-004: Delete after successful run

Architecture:
- Stores checkpoints as JSON on local filesystem
- Path: {base_path}/checkpoints/{pipeline}/latest.json
- Atomic writes via temp file + os.replace
- Metadata includes run_id and custom metadata
"""

from __future__ import annotations

import asyncio
import os
import tempfile
from pathlib import Path
from typing import Any
from uuid import UUID

from bioetl.domain.serialization import deserialize_from_json, serialize_to_json
from bioetl.domain.types import RunID


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
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Save checkpoint atomically using temp file + rename.

        Uses run_in_executor to avoid blocking the event loop.
        """
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(
            None, self._save_sync, pipeline, run_id, metadata
        )

    def _save_sync(
        self,
        pipeline: str,
        run_id: RunID,
        metadata: dict[str, Any] | None,
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
        except Exception:
            # Clean up temp file on error
            temp_file = Path(temp_path)
            if temp_file.exists():
                temp_file.unlink()
            raise

    async def load(self, pipeline: str) -> tuple[RunID, dict[str, Any]] | None:
        """Load last checkpoint.

        Uses run_in_executor to avoid blocking the event loop.
        """
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._load_sync, pipeline)

    def _load_sync(self, pipeline: str) -> tuple[RunID, dict[str, Any]] | None:
        """Synchronous load implementation."""
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
        """
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._list_all_sync)

    def _list_all_sync(self) -> list[str]:
        """Synchronous list_all implementation."""
        prefix = "checkpoints"
        root = self.base_path / prefix
        pipelines: set[str] = set()

        if root.exists():
            for path in root.iterdir():
                if path.is_dir():
                    pipelines.add(path.name)

        return sorted(pipelines)

    async def exists(self, pipeline: str) -> bool:
        """Check if checkpoint exists.

        Uses run_in_executor to avoid blocking the event loop.
        """
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._exists_sync, pipeline)

    def _exists_sync(self, pipeline: str) -> bool:
        """Synchronous exists implementation."""
        key = self._get_key(pipeline)
        return (self.base_path / key).exists()

    def _get_key(self, pipeline: str) -> str:
        return f"checkpoints/{pipeline}/latest.json"

    async def aclose(self) -> None:
        """Close checkpoint storage (no-op for local filesystem)."""
