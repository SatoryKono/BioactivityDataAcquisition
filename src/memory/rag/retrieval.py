"""Helpers for loading and filtering deterministic RAG chunk manifests."""

from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any


def load_chunk_manifest(path: Path) -> list[dict[str, Any]]:
    """Load a JSONL chunk manifest."""
    chunks: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        chunks.append(json.loads(line))
    return chunks


def filter_chunks(
    chunks: Iterable[dict[str, Any]],
    *,
    source_type: str | None = None,
    domain: str | None = None,
    query: str | None = None,
) -> list[dict[str, Any]]:
    """Apply simple deterministic filters to loaded chunk records."""
    lowered_query = query.lower() if query is not None else None
    result: list[dict[str, Any]] = []
    for chunk in chunks:
        if source_type is not None and chunk.get("source_type") != source_type:
            continue
        if domain is not None and chunk.get("domain") != domain:
            continue
        if lowered_query is not None:
            haystack = " ".join(
                str(chunk.get(field, ""))
                for field in ("title", "content", "source_path", "source_type")
            ).lower()
            if lowered_query not in haystack:
                continue
        result.append(chunk)
    return result
