"""Readiness checks for rebuild-only memory artifacts."""

from __future__ import annotations

import json
from pathlib import Path

from memory.rag.validation import (
    capture_rag_git_identity,
    validate_rag_manifest_files,
)
from memory.timeline._common import TIMELINE_MANIFEST_NAME


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


def timeline_events_ready(events_dir: Path, *, repo_root: Path | None = None) -> bool:
    """Return whether timeline projections are intact and version-compatible."""
    if not events_dir.is_dir():
        return False
    event_files = sorted(events_dir.glob("*.jsonl"), key=lambda path: path.name)
    if not event_files:
        return False
    manifest = _load_catalog(events_dir / TIMELINE_MANIFEST_NAME)
    resolved_root = (
        repo_root.resolve()
        if repo_root is not None
        else _discover_repo_root(events_dir)
    )
    if manifest is None:
        return resolved_root is None and all(
            _valid_timeline_jsonl(path) for path in event_files
        )
    entries = manifest.get("files")
    if manifest.get("schema_version") != 1 or not isinstance(entries, list):
        return False
    if not _timeline_manifest_files_valid(events_dir, event_files, entries):
        return False
    return _timeline_manifest_matches_repository(manifest, resolved_root)


def _timeline_manifest_files_valid(
    events_dir: Path,
    event_files: list[Path],
    entries: list[object],
) -> bool:
    """Validate the manifest inventory and each timeline event artifact."""
    expected_names = {path.name for path in event_files}
    if {
        entry.get("path") for entry in entries if isinstance(entry, dict)
    } != expected_names:
        return False
    for entry in entries:
        if not isinstance(entry, dict):
            return False
        path = events_dir / str(entry.get("path", ""))
        if (
            not path.is_file()
            or path.stat().st_size != entry.get("size")
            or _file_sha256(path) != entry.get("sha256")
            or not _valid_timeline_jsonl(path)
        ):
            return False
    return True


def _timeline_manifest_matches_repository(
    manifest: dict[str, object],
    resolved_root: Path | None,
) -> bool:
    """Validate repository identity when timeline events are repo-bound."""
    if resolved_root is None:
        return True
    current = capture_rag_git_identity(resolved_root)
    return (
        manifest.get("git_head_sha") == current["git_head_sha"]
        and manifest.get("working_tree_state") == "clean"
        and current["working_tree_state"] == "clean"
    )


def _file_sha256(path: Path) -> str:
    import hashlib

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _valid_timeline_jsonl(path: Path) -> bool:
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            if not isinstance(row, dict) or not isinstance(row.get("id"), str):
                return False
    except (OSError, UnicodeError, json.JSONDecodeError):
        return False
    return True
