"""Shared immutable input-snapshot resolution helpers."""

from __future__ import annotations

from pathlib import Path
from uuid import UUID

from bioetl.composition.runtime_builders.cached_bronze_snapshot_support import (
    build_cached_bronze_input_snapshot_refs,
)
from bioetl.composition.runtime_builders._run_manifest_data_roots import (
    control_plane_root,
)
from bioetl.domain.control_plane import RunInputSnapshotRef, RunManifest
from bioetl.domain.types import RunID
from bioetl.infrastructure.control_plane import FileRunManifestStore

__all__ = [
    "collect_manifest_input_snapshot_refs",
    "resolve_cached_bronze_input_snapshot_refs",
    "resolve_manifest_input_snapshot_refs",
    "resolve_pipeline_input_snapshot_refs",
]


def resolve_cached_bronze_input_snapshot_refs(
    *,
    cached_bronze: object | None,
    settings: object,
    provider: str,
    entity: str,
) -> tuple[RunInputSnapshotRef, ...]:
    """Resolve immutable snapshots from one cached-Bronze runtime context."""
    if cached_bronze is None or not getattr(cached_bronze, "enabled", False):
        return ()
    bronze_path = getattr(cached_bronze, "bronze_path", None)
    bronze_date = getattr(cached_bronze, "bronze_date", None)
    bronze_root = (
        Path(str(bronze_path))
        if bronze_path is not None
        else Path(str(settings.bronze_path)) / provider / entity
    )
    snapshot_refs = build_cached_bronze_input_snapshot_refs(
        bronze_root=bronze_root,
        bronze_date=_coerce_optional_str(bronze_date),
    )
    if not snapshot_refs:
        raise RuntimeError(
            "Cached Bronze execution requires at least one persisted batch file for snapshot provenance"
        )
    return snapshot_refs


def collect_manifest_input_snapshot_refs(
    manifest: RunManifest,
) -> tuple[RunInputSnapshotRef, ...]:
    """Flatten immutable snapshot refs across all manifest source refs."""
    return tuple(
        snapshot
        for source_ref in manifest.source_refs
        for snapshot in source_ref.input_snapshots
    )


def resolve_manifest_input_snapshot_refs(
    *,
    settings: object,
    manifest_id: str | None = None,
    run_id: str | None = None,
) -> tuple[RunInputSnapshotRef, ...]:
    """Resolve immutable snapshots from one persisted manifest."""
    manifest = _load_manifest(
        settings=settings,
        manifest_id=manifest_id,
        run_id=run_id,
    )
    if manifest is None:
        return ()
    return collect_manifest_input_snapshot_refs(manifest)


def resolve_pipeline_input_snapshot_refs(
    *,
    ctx: object,
    cached_bronze: object | None,
    settings: object,
    provider: str,
    entity: str,
) -> tuple[RunInputSnapshotRef, ...]:
    """Resolve immutable snapshot evidence for one executable pipeline launch."""
    cached_bronze_refs = resolve_cached_bronze_input_snapshot_refs(
        cached_bronze=cached_bronze,
        settings=settings,
        provider=provider,
        entity=entity,
    )
    if cached_bronze_refs:
        return cached_bronze_refs

    parent_manifest_refs = resolve_manifest_input_snapshot_refs(
        settings=settings,
        manifest_id=_coerce_optional_str(getattr(ctx, "replay_of_manifest_id", None)),
        run_id=_coerce_optional_str(getattr(ctx, "replay_of_run_id", None)),
    )
    if parent_manifest_refs:
        return parent_manifest_refs
    return ()


def _load_manifest(
    *,
    settings: object,
    manifest_id: str | None,
    run_id: str | None,
) -> RunManifest | None:
    store = FileRunManifestStore(
        base_path=control_plane_root(settings, "run_manifest"),
    )
    if manifest_id:
        return store.get(manifest_id)
    if not run_id:
        return None
    try:
        return store.get_by_run_id(RunID(UUID(run_id)))
    except ValueError:
        return None


def _coerce_optional_str(value: object | None) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
