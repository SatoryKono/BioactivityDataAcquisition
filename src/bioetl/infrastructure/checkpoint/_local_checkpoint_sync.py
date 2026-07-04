"""Synchronous local checkpoint operations."""

from __future__ import annotations

from pathlib import Path

from bioetl.domain.serialization import serialize_to_json
from bioetl.domain.types import JsonDict, RunID
from bioetl.infrastructure.checkpoint._local_checkpoint_io import (
    atomic_write_text,
    build_history_entry_path,
    extract_manifest_id,
    history_path_from_manifest_index,
    history_run_dir,
    latest_history_checkpoint_path,
    load_checkpoint_tuple,
    manifest_index_path,
    normalize_saved_metadata,
    read_json_file,
)


class LocalCheckpointSyncMixin:
    """Synchronous filesystem implementation for ``LocalCheckpointAdapter``."""

    base_path: Path

    def _save_sync(
        self,
        pipeline: str,
        run_id: RunID,
        metadata: JsonDict | None,
    ) -> None:
        """Synchronous save implementation."""
        full_path = self.base_path / self._get_key(pipeline)
        full_path.parent.mkdir(parents=True, exist_ok=True)
        saved_metadata = normalize_saved_metadata(metadata)
        checkpoint_data = {
            "pipeline": pipeline,
            "run_id": str(run_id),
            "metadata": saved_metadata,
            "version": "2.0",
        }
        checkpoint_json = serialize_to_json(checkpoint_data, ensure_ascii=False)
        atomic_write_text(full_path, checkpoint_json)
        self._write_history_checkpoint(
            pipeline=pipeline,
            run_id=run_id,
            saved_metadata=saved_metadata,
            checkpoint_json=checkpoint_json,
        )

    def _write_history_checkpoint(
        self,
        *,
        pipeline: str,
        run_id: RunID,
        saved_metadata: JsonDict,
        checkpoint_json: str,
    ) -> None:
        history_path = build_history_entry_path(self.base_path, pipeline, run_id)
        history_path.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_text(history_path, checkpoint_json)
        manifest_id = extract_manifest_id(saved_metadata)
        if manifest_id is None:
            return
        manifest_index = {
            "manifest_id": manifest_id,
            "pipeline": pipeline,
            "run_id": str(run_id),
            "history_path": str(history_path.relative_to(self.base_path)),
        }
        index_path = manifest_index_path(self.base_path, manifest_id)
        index_path.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_text(
            index_path,
            serialize_to_json(manifest_index, ensure_ascii=False),
        )

    def _load_sync(self, pipeline: str) -> tuple[RunID, JsonDict] | None:
        """Synchronous load implementation."""
        full_path = self.base_path / self._get_key(pipeline)
        if not full_path.exists():
            return None
        return load_checkpoint_tuple(full_path)

    def _delete_sync(self, pipeline: str) -> None:
        """Synchronous delete implementation for the mutable resume pointer only."""
        full_path = self.base_path / self._get_key(pipeline)
        if full_path.exists():
            full_path.unlink()

    def _list_all_sync(self) -> list[str]:
        """List pipelines with mutable checkpoint pointers."""
        pipelines: set[str] = set()
        if self.base_path.exists():
            for path in self.base_path.iterdir():
                if path.is_file() and path.suffix == ".json":
                    pipelines.add(path.stem)
        return sorted(pipelines)

    def _exists_sync(self, pipeline: str) -> bool:
        """Return whether the mutable checkpoint pointer exists."""
        return (self.base_path / self._get_key(pipeline)).exists()

    def _get_key(self, pipeline: str) -> str:
        """Return flat checkpoint filename for one pipeline."""
        return f"{pipeline}.json"

    def _load_for_run_sync(
        self,
        pipeline: str,
        run_id: RunID,
    ) -> tuple[RunID, JsonDict] | None:
        history_dir = history_run_dir(self.base_path, pipeline, run_id)
        if not history_dir.exists():
            return None
        candidates = sorted(
            path for path in history_dir.iterdir() if path.suffix == ".json"
        )
        if not candidates:
            return None
        return load_checkpoint_tuple(candidates[-1])

    def _load_for_manifest_id_sync(
        self,
        manifest_id: str,
    ) -> tuple[RunID, JsonDict] | None:
        index_path = manifest_index_path(self.base_path, manifest_id)
        if not index_path.exists():
            return None
        index = read_json_file(index_path)
        history_path = index.get("history_path") if isinstance(index, dict) else None
        if not isinstance(history_path, str) or not history_path:
            return None
        full_history_path = history_path_from_manifest_index(
            self.base_path,
            history_path,
        )
        if not full_history_path.exists():
            return None
        return load_checkpoint_tuple(full_history_path)

    def _load_latest_for_pipeline_sync(
        self,
        pipeline: str,
    ) -> tuple[RunID, JsonDict] | None:
        latest_path = latest_history_checkpoint_path(self.base_path, pipeline)
        if latest_path is None:
            return None
        return load_checkpoint_tuple(latest_path)
