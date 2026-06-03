"""Manifest and source-ref extraction helpers for Control Plane identity."""

from __future__ import annotations

from collections.abc import Sequence

from bioetl.domain.control_plane import (
    RunArtifactRef,
    RunInputSnapshotRef,
    RunManifest,
    RunSourceRef,
)
from bioetl.domain.normalization import compute_input_snapshot_identity_fingerprint
from bioetl.interfaces.http.control_plane_identity.formatting import (
    is_present,
    join_non_empty,
)


def identity_graph_diagnostics(manifest: RunManifest) -> dict[str, object]:
    """Return identity graph diagnostics embedded in known manifest payloads."""
    diagnostics: dict[str, object] = {}
    for payload in (
        manifest.runtime_config,
        manifest.resolved_config,
        manifest.launch_context,
    ):
        for key in (
            "identity_graph",
            "identity_graph_diagnostics",
            "diagnostics",
            "reproducibility_diagnostics",
        ):
            value = payload.get(key)
            if isinstance(value, dict):
                diagnostics.update(
                    {str(item_key): item for item_key, item in value.items()}
                )
    return diagnostics


def diagnostic_value(
    diagnostics: dict[str, object],
    *keys: str,
) -> object | None:
    for key in keys:
        value = diagnostics.get(key)
        if is_present(value):
            return value
    return None


def correlation_anchor_gaps(diagnostics: dict[str, object]) -> dict[str, object]:
    value = diagnostics.get("correlation_anchor_gaps")
    return dict(value) if isinstance(value, dict) else {}


def input_snapshots(manifest: RunManifest) -> tuple[RunInputSnapshotRef, ...]:
    snapshots: list[RunInputSnapshotRef] = []
    for source_ref in manifest.source_refs:
        snapshots.extend(source_ref.input_snapshots)
    return tuple(snapshots)


def input_snapshot_fingerprint(
    snapshots: tuple[RunInputSnapshotRef, ...],
) -> str | None:
    if not snapshots:
        return None
    payload: list[object] = [
        {
            "snapshot_id": item.snapshot_id,
            "content_hash": item.content_hash,
            "immutable_uri": item.immutable_uri,
            "query_fingerprint": item.query_fingerprint,
        }
        for item in snapshots
    ]
    return compute_input_snapshot_identity_fingerprint(payload)


def source_ref_values(source_refs: Sequence[RunSourceRef]) -> list[str]:
    return [
        value
        for item in source_refs
        if (
            value := join_non_empty(
                (item.provider, item.entity, item.pipeline_name), "/"
            )
        )
    ]


def artifact_ref_values(artifacts: Sequence[RunArtifactRef]) -> list[str]:
    return [
        ref
        for item in artifacts
        if (ref := join_non_empty((item.layer, item.path), ":"))
    ]


def extract_manifest_anchors(manifest_data: dict[str, object]) -> list[object]:
    """Extract legacy HTTP identity anchor values from manifest-like mappings."""
    from bioetl.interfaces.http.control_plane_identity.anchor_values import (
        anchor_values_from_mapping,
    )

    payload = dict(manifest_data)
    provider_entity = join_non_empty(
        (payload.get("provider"), payload.get("entity")), "."
    )
    if provider_entity:
        payload["provider_entity"] = provider_entity
    return anchor_values_from_mapping(
        payload,
        source="manifest",
        anchor_names=(
            "run_id",
            "manifest_id",
            "pipeline_name",
            "provider_entity",
        ),
    )


__all__ = [
    "artifact_ref_values",
    "correlation_anchor_gaps",
    "diagnostic_value",
    "extract_manifest_anchors",
    "identity_graph_diagnostics",
    "input_snapshot_fingerprint",
    "input_snapshots",
    "source_ref_values",
]
