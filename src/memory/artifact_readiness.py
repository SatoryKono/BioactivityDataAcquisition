"""Readiness checks for rebuild-only memory artifacts."""

from __future__ import annotations

from pathlib import Path


def rag_chunks_ready(chunks_path: Path) -> bool:
    """Return whether the RAG chunk manifest is usable for retrieval."""
    return chunks_path.is_file() and chunks_path.stat().st_size > 0


def timeline_events_ready(events_dir: Path) -> bool:
    """Return whether timeline event projections have been generated."""
    if not events_dir.is_dir():
        return False
    return any(
        path.is_file() and path.suffix == ".jsonl" for path in events_dir.iterdir()
    )
