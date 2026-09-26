"""Live snapshot reference helpers for Bronze metadata writes."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bioetl.domain.models.metadata import InputSnapshotRef, SourceMetadata


def build_bronze_source_metadata_with_live_snapshot(
    *,
    source_metadata: SourceMetadata | None,
    snapshot: InputSnapshotRef | None,
) -> SourceMetadata | None:
    """Return source metadata enriched with the live snapshot when available."""
    if snapshot is None:
        return source_metadata
    if source_metadata is None:
        from bioetl.domain.models.metadata import SourceMetadata

        return SourceMetadata(type="api", input_snapshots=[snapshot])
    return attach_live_snapshot_to_source_metadata(
        source_metadata=source_metadata,
        snapshot=snapshot,
    )


def attach_live_snapshot_to_source_metadata(
    *,
    source_metadata: SourceMetadata,
    snapshot: InputSnapshotRef | None,
) -> SourceMetadata | None:
    """Attach the snapshot in-place while preserving ``source_metadata`` identity."""
    if snapshot is None:
        return source_metadata
    for existing in source_metadata.input_snapshots:
        if (
            existing.snapshot_id == snapshot.snapshot_id
            and existing.content_hash == snapshot.content_hash
            and existing.immutable_uri == snapshot.immutable_uri
        ):
            return source_metadata

    source_metadata.input_snapshots.append(snapshot)
    return source_metadata


def build_live_input_snapshot_ref_if_available(
    *,
    base_path: Path,
    relative_path: str,
    query_string: str | None,
) -> InputSnapshotRef | None:
    """Build a live snapshot ref only when the Bronze output exists."""
    full_path = base_path / relative_path
    if not full_path.exists():
        return None
    return build_live_input_snapshot_ref(
        full_path=full_path,
        relative_path=relative_path,
        query_string=query_string,
    )


def build_live_input_snapshot_ref(
    *,
    full_path: Path,
    relative_path: str,
    query_string: str | None,
) -> InputSnapshotRef:
    """Build a replayable snapshot ref from the persisted Bronze batch file."""
    from bioetl.domain.models.metadata import InputSnapshotRef

    content_hash = compute_file_sha256(full_path)
    query_fingerprint = (
        None
        if not query_string
        else hashlib.sha256(query_string.encode("utf-8")).hexdigest()
    )
    portable_relative_path = Path(relative_path).as_posix()
    return InputSnapshotRef(
        snapshot_id=content_addressed_snapshot_id(content_hash),
        content_hash=content_hash,
        immutable_uri=f"bronze://{portable_relative_path}",
        query_fingerprint=query_fingerprint,
        captured_at=None,
    )


def content_addressed_snapshot_id(content_hash: str) -> str:
    """Return a portable snapshot identity derived only from captured content."""
    return f"sha256:{content_hash}"


def compute_file_sha256(path: Path) -> str:
    """Hash persisted Bronze batch bytes for replay-safe provenance."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
