"""Select immutable replay inputs through the injected manifest port."""

from __future__ import annotations

from collections.abc import Callable
from uuid import UUID

from bioetl.domain.control_plane import RunInputSnapshotRef, RunManifest
from bioetl.domain.ports import RunManifestPort
from bioetl.domain.types import RunID


def collect_manifest_input_snapshot_refs(
    manifest: RunManifest,
) -> tuple[RunInputSnapshotRef, ...]:
    """Preserve source and snapshot order when flattening manifest inputs."""
    return tuple(
        snapshot
        for source in manifest.source_refs
        for snapshot in source.input_snapshots
    )


def resolve_manifest_input_snapshot_refs(
    *,
    store: RunManifestPort,
    manifest_id: str | None = None,
    run_id: str | None = None,
) -> tuple[RunInputSnapshotRef, ...]:
    """Prefer manifest identity, falling back to a valid run identity on a miss.

    Invalid UUID text means no usable run identity. Storage and corruption
    errors propagate, including ValueError from a manifest decoder.
    """
    if manifest_id:
        manifest = store.get(manifest_id)
        if manifest is not None:
            return collect_manifest_input_snapshot_refs(manifest)
    if not run_id:
        return ()
    try:
        typed_run_id = RunID(UUID(run_id))
    except ValueError:
        return ()
    manifest = store.get_by_run_id(typed_run_id)
    return () if manifest is None else collect_manifest_input_snapshot_refs(manifest)


def resolve_pipeline_input_snapshot_refs(
    *,
    cached_bronze_enabled: bool,
    cached_bronze_refs: tuple[RunInputSnapshotRef, ...],
    load_parent_refs: Callable[[], tuple[RunInputSnapshotRef, ...]],
) -> tuple[RunInputSnapshotRef, ...]:
    """Select cached inputs first, including an explicitly enabled empty cache.

    Parent I/O remains lazy so an enabled cache never reads a replay manifest.
    The callback is assembled around an injected RunManifestPort by composition.
    """
    if cached_bronze_enabled or cached_bronze_refs:
        return cached_bronze_refs
    return load_parent_refs()
