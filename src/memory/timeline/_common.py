"""Shared helpers for deterministic timeline event projection."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from memory.resources import MEMORY_ROOT

DEFAULT_EVENTS_DIR = MEMORY_ROOT / "timeline" / "events"


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> Path:
    """Write a deterministic JSONL artifact."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True, ensure_ascii=True))
            handle.write("\n")
    return path


def read_json(path: Path) -> dict[str, Any]:
    """Load a JSON object from disk."""
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    """Load newline-delimited JSON rows from disk."""
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows
