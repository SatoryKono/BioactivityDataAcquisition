"""Checkpoint identity replacement after a committed manifest successor."""

from __future__ import annotations

from dataclasses import asdict, replace

from bioetl.domain.control_plane import RunManifest
from bioetl.domain.normalization import compute_input_snapshot_identity_fingerprint
from bioetl.domain.types.checkpoint_metadata import CheckpointMetadata


def metadata_with_manifest(
    metadata: CheckpointMetadata | None,
    manifest: RunManifest,
) -> CheckpointMetadata:
    """Copy snapshot and execution identity from a committed manifest."""
    snapshots = tuple(s for ref in manifest.source_refs for s in ref.input_snapshots)
    identity = replace(
        metadata or CheckpointMetadata(),
        manifest_id=manifest.manifest_id,
        execution_fingerprint=manifest.execution_fingerprint,
        input_snapshot_ids=tuple(snapshot.snapshot_id for snapshot in snapshots),
        input_snapshot_refs=tuple(
            {
                **asdict(snapshot),
                "captured_at": snapshot.captured_at.isoformat()
                if snapshot.captured_at
                else None,
            }
            for snapshot in snapshots
        ),
        input_snapshot_fingerprint=compute_input_snapshot_identity_fingerprint(
            snapshots
        ),
    )
    return rebind_checkpoint_metadata(identity, identity)


def rebind_checkpoint_metadata(
    metadata: CheckpointMetadata,
    identity: CheckpointMetadata,
) -> CheckpointMetadata:
    """Replace stale manifest anchors while preserving checkpoint progress."""
    run_context = metadata.run_context
    if run_context is not None:
        run_context = {
            **run_context,
            "manifest_id": identity.manifest_id,
            "execution_fingerprint": identity.execution_fingerprint,
            "input_snapshot_fingerprint": identity.input_snapshot_fingerprint,
        }
    return replace(
        metadata,
        manifest_id=identity.manifest_id,
        execution_fingerprint=identity.execution_fingerprint,
        input_snapshot_ids=identity.input_snapshot_ids,
        input_snapshot_refs=identity.input_snapshot_refs,
        input_snapshot_fingerprint=identity.input_snapshot_fingerprint,
        run_context=run_context,
    )
