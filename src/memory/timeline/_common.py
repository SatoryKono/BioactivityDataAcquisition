"""Shared helpers for deterministic timeline event projection."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from memory.rag.validation import capture_rag_git_identity
from memory.resources import MEMORY_ROOT
from memory.storage import atomic_write_json

DEFAULT_EVENTS_DIR = MEMORY_ROOT / "timeline" / "events"
TIMELINE_MANIFEST_NAME = "timeline_manifest.json"


def dedupe_preserve_order(values: list[str]) -> list[str]:
    """Return a stable de-duplicated list preserving original order."""
    result: list[str] = []
    for value in values:
        if value not in result:
            result.append(value)
    return result


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> Path:
    """Write a deterministic JSONL artifact."""
    path.parent.mkdir(parents=True, exist_ok=True)
    from scripts.engineering.common.repo_paths import REPO_ROOT, resolve_output_path

    path = resolve_output_path(path, root=REPO_ROOT)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True, ensure_ascii=True))
            handle.write("\n")
    return path


def read_json(path: Path) -> dict[str, Any]:
    """Load a JSON object from disk."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError(f"Expected JSON object in {path}")
    return payload


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    """Load newline-delimited JSON rows from disk."""
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_timeline_manifest(root: Path, events_dir: Path) -> Path:
    """Bind generated event projections to their repository version and bytes."""
    event_files = sorted(events_dir.glob("*.jsonl"), key=lambda path: path.name)
    payload = {
        "schema_version": 1,
        **capture_rag_git_identity(root),
        "files": [
            {
                "path": path.name,
                "sha256": _sha256(path),
                "size": path.stat().st_size,
            }
            for path in event_files
        ],
    }
    manifest_path = events_dir / TIMELINE_MANIFEST_NAME
    atomic_write_json(manifest_path, payload)
    return manifest_path
