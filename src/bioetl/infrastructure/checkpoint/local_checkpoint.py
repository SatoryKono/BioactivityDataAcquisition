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

__all__ = ["LocalCheckpointAdapter"]


import asyncio
import os
import tempfile
import time
from pathlib import Path
from uuid import UUID

from bioetl.domain.serialization import deserialize_from_json, serialize_to_json
from bioetl.domain.types import JsonDict, RunID


def _history_run_dir(base_path: Path, pipeline: str, run_id: RunID) -> Path:
    return base_path / ".history" / "by_pipeline" / pipeline / str(run_id)


def _build_history_entry_path(base_path: Path, pipeline: str, run_id: RunID) -> Path:
    return _history_run_dir(base_path, pipeline, run_id) / f"{time.time_ns()}.json"


def _manifest_index_path(base_path: Path, manifest_id: str) -> Path:
    return base_path / ".history" / "by_manifest" / f"{manifest_id}.json"


def _history_path_from_manifest_index(base_path: Path, history_path: str) -> Path:
    """Resolve history paths written on either Windows or POSIX hosts."""
    normalized = history_path.replace("\\", "/")
    return base_path.joinpath(*normalized.split("/"))


def _extract_manifest_id(metadata: JsonDict) -> str | None:
    manifest_id = metadata.get("manifest_id")
    if manifest_id is None and isinstance(metadata.get("run_context"), dict):
        manifest_id = metadata["run_context"].get("manifest_id")
    if manifest_id is None:
        return None
    text = str(manifest_id).strip()
    return text or None


def _normalize_saved_metadata(metadata: JsonDict | None) -> JsonDict:
    """Return caller-owned checkpoint metadata without adding wall-clock state."""
    return dict(metadata or {})


def _read_json_file(path: Path) -> JsonDict:
    with open(path, encoding="utf-8") as f:
        payload = f.read()
    data = deserialize_from_json(payload)
    if not isinstance(data, dict):
        raise ValueError("Checkpoint data must be a dictionary")
    return data


def _normalize_loaded_metadata(path: Path, metadata: object) -> JsonDict:
    if not isinstance(metadata, dict):
        return {}
    normalized = dict(metadata)
    normalized.setdefault("checkpoint_saved_at_epoch_seconds", path.stat().st_mtime)
    return normalized


def _load_checkpoint_tuple(path: Path) -> tuple[RunID, JsonDict]:
    checkpoint_data = _read_json_file(path)
    run_id = RunID(UUID(checkpoint_data["run_id"]))
    metadata = _normalize_loaded_metadata(path, checkpoint_data.get("metadata", {}))
    return (run_id, metadata)


def _latest_history_checkpoint_path(base_path: Path, pipeline: str) -> Path | None:
    history_root = base_path / ".history" / "by_pipeline" / pipeline
    if not history_root.exists():
        return None
    candidates: list[Path] = []
    for run_dir in history_root.iterdir():
        if not run_dir.is_dir():
            continue
        for candidate in run_dir.iterdir():
            if not candidate.is_file() or candidate.suffix != ".json":
                continue
            candidates.append(candidate)
    if not candidates:
        return None
    return max(candidates, key=lambda path: (path.stat().st_mtime_ns, path.name))


def _atomic_write_text(path: Path, payload: str) -> None:
    fd, temp_path = tempfile.mkstemp(
        dir=path.parent,
        prefix=".checkpoint_",
        suffix=".tmp",
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(payload)
        Path(temp_path).replace(path)
    except (OSError, ValueError, TypeError, RuntimeError):
        temp_file = Path(temp_path)
        if temp_file.exists():
            temp_file.unlink()
        raise


class LocalCheckpointAdapter:
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
        saved_metadata = _normalize_saved_metadata(metadata)

        checkpoint_data = {
            "pipeline": pipeline,
            "run_id": str(run_id),
            "metadata": saved_metadata,
            "version": "2.0",
        }
        checkpoint_json = serialize_to_json(checkpoint_data, ensure_ascii=False)
        _atomic_write_text(full_path, checkpoint_json)
        history_path = _build_history_entry_path(self.base_path, pipeline, run_id)
        history_path.parent.mkdir(parents=True, exist_ok=True)
        _atomic_write_text(history_path, checkpoint_json)
        manifest_id = _extract_manifest_id(saved_metadata)
        if manifest_id is not None:
            manifest_index = {
                "manifest_id": manifest_id,
                "pipeline": pipeline,
                "run_id": str(run_id),
                "history_path": str(history_path.relative_to(self.base_path)),
            }
            _manifest_index_path(self.base_path, manifest_id).parent.mkdir(
                parents=True,
                exist_ok=True,
            )
            _atomic_write_text(
                _manifest_index_path(self.base_path, manifest_id),
                serialize_to_json(manifest_index, ensure_ascii=False),
            )

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
        return _load_checkpoint_tuple(full_path)

    async def delete(self, pipeline: str) -> None:
        """Delete checkpoint.

        Uses run_in_executor to avoid blocking the event loop.

        Args:
            pipeline: Pipeline.
        """
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self._delete_sync, pipeline)

    def _delete_sync(self, pipeline: str) -> None:
        """Synchronous delete implementation for the mutable resume pointer only."""
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

    async def load_for_run(
        self,
        pipeline: str,
        run_id: RunID,
    ) -> tuple[RunID, JsonDict] | None:
        """Load the latest immutable checkpoint evidence stored for one run."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None,
            self._load_for_run_sync,
            pipeline,
            run_id,
        )

    def _load_for_run_sync(
        self,
        pipeline: str,
        run_id: RunID,
    ) -> tuple[RunID, JsonDict] | None:
        history_dir = _history_run_dir(self.base_path, pipeline, run_id)
        if not history_dir.exists():
            return None
        candidates = sorted(
            path for path in history_dir.iterdir() if path.suffix == ".json"
        )
        if not candidates:
            return None
        return _load_checkpoint_tuple(candidates[-1])

    async def load_for_manifest_id(
        self,
        manifest_id: str,
    ) -> tuple[RunID, JsonDict] | None:
        """Load immutable checkpoint evidence indexed by manifest identity."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None,
            self._load_for_manifest_id_sync,
            manifest_id,
        )

    def _load_for_manifest_id_sync(
        self,
        manifest_id: str,
    ) -> tuple[RunID, JsonDict] | None:
        index_path = _manifest_index_path(self.base_path, manifest_id)
        if not index_path.exists():
            return None
        index = _read_json_file(index_path)
        history_path = index.get("history_path") if isinstance(index, dict) else None
        if not isinstance(history_path, str) or not history_path:
            return None
        full_history_path = _history_path_from_manifest_index(
            self.base_path,
            history_path,
        )
        if not full_history_path.exists():
            return None
        return _load_checkpoint_tuple(full_history_path)

    async def load_latest_for_pipeline(
        self,
        pipeline: str,
    ) -> tuple[RunID, JsonDict] | None:
        """Load latest immutable checkpoint evidence across all runs for one pipeline."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None,
            self._load_latest_for_pipeline_sync,
            pipeline,
        )

    def _load_latest_for_pipeline_sync(
        self,
        pipeline: str,
    ) -> tuple[RunID, JsonDict] | None:
        latest_path = _latest_history_checkpoint_path(self.base_path, pipeline)
        if latest_path is None:
            return None
        return _load_checkpoint_tuple(latest_path)

    async def aclose(self) -> None:
        """Close checkpoint storage (no-op for local filesystem)."""
