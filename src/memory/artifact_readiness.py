"""Readiness checks for rebuild-only memory artifacts."""

from __future__ import annotations

import json
from pathlib import Path

from memory.rag.validation import (
    capture_rag_git_identity,
    validate_rag_manifest_files,
)


def _discover_repo_root(path: Path) -> Path | None:
    for candidate in (path.resolve(), *path.resolve().parents):
        if (candidate / ".git").exists() and (candidate / "src" / "memory").exists():
            return candidate
    return None


def _load_catalog(catalog_path: Path) -> dict[str, object] | None:
    try:
        payload = json.loads(catalog_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _can_use_metadata_fast_path(root: Path, catalog: dict[str, object]) -> bool:
    current_identity = capture_rag_git_identity(root)
    return (
        catalog.get("git_head_sha") is not None
        and catalog.get("git_head_sha") == current_identity["git_head_sha"]
        and catalog.get("working_tree_state") == "clean"
        and current_identity["working_tree_state"] == "clean"
    )


def rag_chunks_ready(
    chunks_path: Path,
    *,
    repo_root: Path | None = None,
    require_build_scope: str | None = None,
) -> bool:
    """Return whether a complete RAG manifest pair is safe for retrieval."""
    catalog_path = chunks_path.with_name("corpus_catalog.json")
    if not (
        catalog_path.is_file()
        and catalog_path.stat().st_size > 0
        and chunks_path.is_file()
        and chunks_path.stat().st_size > 0
    ):
        return False

    catalog = _load_catalog(catalog_path)
    if catalog is None:
        return False
    resolved_root = (
        repo_root.resolve()
        if repo_root is not None
        else _discover_repo_root(chunks_path)
    )
    verify_sources = resolved_root is not None
    if resolved_root is not None and _can_use_metadata_fast_path(
        resolved_root, catalog
    ):
        verify_sources = False
    validation_root = resolved_root or chunks_path.parent
    report = validate_rag_manifest_files(
        validation_root,
        catalog_path,
        chunks_path,
        require_build_scope=require_build_scope,
        verify_sources=verify_sources,
    )
    return report.ok


def timeline_events_ready(events_dir: Path) -> bool:
    """Return whether timeline event projections have been generated."""
    if not events_dir.is_dir():
        return False
    return any(
        path.is_file() and path.suffix == ".jsonl" for path in events_dir.iterdir()
    )
