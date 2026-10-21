"""Select current manifests while retaining history in manifest catalogs."""

from __future__ import annotations

from bioetl.domain.control_plane.run_manifest import RunManifest


def current_run_manifests(
    manifests: tuple[RunManifest, ...],
) -> tuple[RunManifest, ...]:
    """Keep chain tips in catalog order, regardless of timestamp or ID order."""
    predecessor_ids = {manifest.predecessor_manifest_id for manifest in manifests}
    return tuple(
        manifest
        for manifest in manifests
        if manifest.manifest_id not in predecessor_ids
    )
