"""Shared cached-Bronze snapshot helpers for exact-replay provenance."""

from __future__ import annotations

import hashlib
from pathlib import Path
from bioetl.domain.context import PipelineRunContext
from bioetl.domain.control_plane.reproducibility_policy import (
    STRICT_PERSISTENCE_PROFILES,
    normalize_required_persistence_profile,
)

from bioetl.domain.control_plane import RunInputSnapshotRef

__all__ = [
    "CACHED_BRONZE_EMPTY_SNAPSHOT_PROVENANCE_MESSAGE",
    "build_cached_bronze_input_snapshot_refs",
    "require_cached_bronze_input_snapshot_refs",
]

CACHED_BRONZE_EMPTY_SNAPSHOT_PROVENANCE_MESSAGE = (
    "Cached Bronze execution requires at least one persisted batch file "
    "for snapshot provenance"
)


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

    snapshot_refs = []
    for batch_file in batch_files:
        with batch_file.open("rb") as stream:
            content_hash = hashlib.file_digest(stream, "sha256").hexdigest()
        relative_path = batch_file.relative_to(bronze_root).as_posix()
        snapshot_refs.append(
            RunInputSnapshotRef(
                snapshot_id=f"sha256:{content_hash}",
                content_hash=content_hash,
                immutable_uri=f"bronze://{relative_path}",
                # Local mtimes are not authoritative capture timestamps.
                captured_at=None,
            )
        )
    # Persist snapshot refs in stable identity order so replay metadata
    # does not depend on filesystem enumeration or content hash/path interplay.
    return tuple(sorted(snapshot_refs, key=lambda ref: ref.snapshot_id))


def require_cached_bronze_input_snapshot_refs(
    *,
    bronze_root: Path,
    bronze_date: str | None,
) -> tuple[RunInputSnapshotRef, ...]:
    """Return cached-Bronze snapshot refs or fail closed when none are present."""
    snapshot_refs = build_cached_bronze_input_snapshot_refs(
        bronze_root=bronze_root,
        bronze_date=bronze_date,
    )
    if not snapshot_refs:
        raise RuntimeError(CACHED_BRONZE_EMPTY_SNAPSHOT_PROVENANCE_MESSAGE)
    return snapshot_refs


def _coerce_optional_str(value: object | None) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def fail_fast_empty_explicit_cached_bronze(ctx: PipelineRunContext) -> None:
    cached_bronze = getattr(ctx, "cached_bronze", None)
    if cached_bronze is None or not getattr(cached_bronze, "enabled", False):
        return
    strict = bool(getattr(ctx, "exact_replay", False)) or (
        normalize_required_persistence_profile(
            getattr(ctx, "required_persistence_profile", None)
        )
        in STRICT_PERSISTENCE_PROFILES
    )
    # degraded_observable must persist the run manifest before failing so the
    # audit trail lands; strict profiles fail closed without artifacts.
    if not strict:
        return
    bronze_path = _coerce_optional_str(getattr(cached_bronze, "bronze_path", None))
    if bronze_path is None:
        return
    require_cached_bronze_input_snapshot_refs(
        bronze_root=Path(bronze_path),
        bronze_date=_coerce_optional_str(getattr(cached_bronze, "bronze_date", None)),
    )
