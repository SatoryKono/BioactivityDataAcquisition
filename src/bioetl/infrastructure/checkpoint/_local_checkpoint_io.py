"""Filesystem helpers for local checkpoint storage."""

from __future__ import annotations

import os
import tempfile
import time
from pathlib import Path
from uuid import UUID

from bioetl.domain.serialization import deserialize_from_json
from bioetl.domain.types import JsonDict, RunID
from bioetl.infrastructure.checkpoint._local_checkpoint_integrity import (
    inject_checkpoint_checksum_verdict,
    strip_reserved_checksum_metadata,
)

_HISTORY_DIR_NAME = ".history"


def history_run_dir(base_path: Path, pipeline: str, run_id: RunID) -> Path:
    return base_path / _HISTORY_DIR_NAME / "by_pipeline" / pipeline / str(run_id)


def build_history_entry_path(base_path: Path, pipeline: str, run_id: RunID) -> Path:
    return history_run_dir(base_path, pipeline, run_id) / f"{time.time_ns()}.json"


def manifest_index_path(base_path: Path, manifest_id: str) -> Path:
    return base_path / _HISTORY_DIR_NAME / "by_manifest" / f"{manifest_id}.json"


def history_path_from_manifest_index(base_path: Path, history_path: str) -> Path:
    """Resolve history paths written on either Windows or POSIX hosts."""
    normalized = history_path.replace("\\", "/")
    return base_path.joinpath(*normalized.split("/"))


def extract_manifest_id(metadata: JsonDict) -> str | None:
    manifest_id = metadata.get("manifest_id")
    if manifest_id is None and isinstance(metadata.get("run_context"), dict):
        manifest_id = metadata["run_context"].get("manifest_id")
    if manifest_id is None:
        return None
    text = str(manifest_id).strip()
    return text or None


def normalize_saved_metadata(metadata: JsonDict | None) -> JsonDict:
    """Return caller-owned checkpoint metadata without adding wall-clock state."""
    return strip_reserved_checksum_metadata(metadata)


def read_json_file(path: Path) -> JsonDict:
    with open(path, encoding="utf-8") as f:
        payload = f.read()
    data = deserialize_from_json(payload)
    if not isinstance(data, dict):
        raise ValueError("Checkpoint data must be a dictionary")
    return data


def normalize_loaded_metadata(
    path: Path,
    checkpoint_data: JsonDict,
    metadata: object,
) -> JsonDict:
    if not isinstance(metadata, dict):
        raise ValueError("Checkpoint metadata must be a dictionary")
    normalized = dict(metadata)
    normalized = inject_checkpoint_checksum_verdict(checkpoint_data, normalized)
    normalized.setdefault("checkpoint_saved_at_epoch_seconds", path.stat().st_mtime)
    return normalized


def load_checkpoint_tuple(path: Path) -> tuple[RunID, JsonDict]:
    checkpoint_data = read_json_file(path)
    run_id = RunID(UUID(checkpoint_data["run_id"]))
    metadata = normalize_loaded_metadata(
        path,
        checkpoint_data,
        checkpoint_data.get("metadata", {}),
    )
    return (run_id, metadata)


def latest_history_checkpoint_path(base_path: Path, pipeline: str) -> Path | None:
    history_root = base_path / _HISTORY_DIR_NAME / "by_pipeline" / pipeline
    if not history_root.exists():
        return None
    candidates: list[Path] = []
    for run_dir in history_root.iterdir():
        if not run_dir.is_dir():
            continue
        for candidate in run_dir.iterdir():
            if candidate.is_file() and candidate.suffix == ".json":
                candidates.append(candidate)
    if not candidates:
        return None
    return max(candidates, key=lambda path: (path.stat().st_mtime_ns, path.name))


def atomic_write_text(path: Path, payload: str) -> None:
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
