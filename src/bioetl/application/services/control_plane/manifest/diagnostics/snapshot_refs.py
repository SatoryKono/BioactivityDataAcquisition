"""Input-snapshot reference helpers for manifest diagnostics."""

from __future__ import annotations

from bioetl.application.services.control_plane.manifest.snapshot_payloads import (
    manifest_input_snapshot_trace_refs,
)
from bioetl.domain.control_plane import RunManifest
from bioetl.domain.normalization import (
    compute_input_snapshot_identity_fingerprint as compute_snapshot_identity_fingerprint,
)


def collect_input_snapshot_refs(manifest: RunManifest) -> list[dict[str, object]]:
    """Return deterministic flattened snapshot provenance extracted from source refs."""
    return manifest_input_snapshot_trace_refs(manifest)


def collect_input_snapshot_ids(input_snapshots: list[dict[str, object]]) -> list[str]:
    """Return deterministic snapshot identities for resume/exact-replay anchors."""
    return [
        str(snapshot_id)
        for snapshot_id in (snapshot.get("snapshot_id") for snapshot in input_snapshots)
        if snapshot_id is not None
    ]


def collect_input_snapshot_content_hashes(
    input_snapshots: list[dict[str, object]],
) -> list[str]:
    """Return deterministic snapshot content hashes for operator inspection."""
    return [
        str(content_hash)
        for content_hash in (
            snapshot.get("content_hash") for snapshot in input_snapshots
        )
        if content_hash is not None
    ]


def compute_input_snapshot_identity_fingerprint(
    input_snapshots: list[dict[str, object]],
) -> str | None:
    """Compute the same stable replay-anchor fingerprint shape used by checkpoints."""
    return compute_snapshot_identity_fingerprint(list(input_snapshots))


__all__ = [
    "collect_input_snapshot_content_hashes",
    "collect_input_snapshot_ids",
    "collect_input_snapshot_refs",
    "compute_input_snapshot_identity_fingerprint",
]
