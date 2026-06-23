"""Shared cached-Bronze snapshot helpers for exact-replay provenance."""

from __future__ import annotations

import hashlib
from pathlib import Path

from bioetl.domain.control_plane import RunInputSnapshotRef

__all__ = [
    "build_cached_bronze_input_snapshot_refs",
]


def build_cached_bronze_input_snapshot_refs(
    *,
    bronze_root: Path,
    bronze_date: str | None,
) -> tuple[RunInputSnapshotRef, ...]:
    """Return deterministic batch-level snapshot refs for cached-Bronze replay."""
    search_root = bronze_root / bronze_date if bronze_date else bronze_root
    if not search_root.exists():
        return ()

    pattern = "batch_*.jsonl.zst" if bronze_date else "**/batch_*.jsonl.zst"
    batch_files = sorted(search_root.glob(pattern))
    if not batch_files:
        return ()

    snapshot_refs = [
        _build_cached_bronze_snapshot_ref(
            bronze_root=bronze_root,
            batch_file=batch_file,
        )
        for batch_file in batch_files
    ]
    # Persist snapshot refs in stable identity order so replay metadata
    # does not depend on filesystem enumeration or content hash/path interplay.
    return tuple(sorted(snapshot_refs, key=lambda ref: ref.snapshot_id))


def _build_cached_bronze_snapshot_ref(
    *,
    bronze_root: Path,
    batch_file: Path,
) -> RunInputSnapshotRef:
    """Build one immutable snapshot ref for one cached Bronze batch file."""
    content_hash = _compute_cached_bronze_batch_content_hash(batch_file)
    relative_path = batch_file.relative_to(bronze_root).as_posix()
    snapshot_id = _content_addressed_snapshot_id(content_hash)
    return RunInputSnapshotRef(
        snapshot_id=snapshot_id,
        content_hash=content_hash,
        immutable_uri=f"bronze://{relative_path}",
        # Cached Bronze files are immutable replay inputs; local mtimes are not
        # authoritative capture timestamps and should not leak into artifacts.
        captured_at=None,
    )


def _content_addressed_snapshot_id(content_hash: str) -> str:
    """Return a portable snapshot identity derived only from captured content."""
    return f"sha256:{content_hash}"


def _compute_cached_bronze_batch_content_hash(batch_file: Path) -> str:
    """Compute the content hash for one persisted cached-Bronze batch file."""
    digest = hashlib.sha256()
    with batch_file.open("rb") as stream:
        while True:
            chunk = stream.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()
