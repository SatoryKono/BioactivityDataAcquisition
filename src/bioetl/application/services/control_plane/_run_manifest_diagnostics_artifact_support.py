"""Artifact and stable-text helpers for manifest diagnostics summary assembly."""

from __future__ import annotations

from bioetl.domain.control_plane import RunManifest


def sorted_text_items(value: object) -> list[str]:
    """Return unique text items in stable content order."""
    if not isinstance(value, (list, tuple, set, frozenset)):
        return []
    return sorted({text for item in value if (text := str(item).strip())})


def artifact_ref_sort_key(artifact_ref: dict[str, object]) -> tuple[str, ...]:
    """Return a stable ordering key for concrete produced artifacts."""
    return (
        str(artifact_ref.get("stage") or ""),
        str(artifact_ref.get("dataset_ref") or artifact_ref.get("artifact_id") or ""),
        str(artifact_ref.get("lineage_fragment_id") or ""),
        str(artifact_ref.get("artifact_path") or ""),
        str(artifact_ref.get("event_type") or ""),
    )


def build_trace_artifact_ref(
    artifact_ref: dict[str, object],
) -> dict[str, object]:
    """Return the concrete produced-artifact shape used by replay trace output."""
    ordered_keys = (
        "event_type",
        "stage",
        "artifact_id",
        "dataset_ref",
        "lineage_fragment_id",
        "artifact_path",
        "metadata_path",
        "artifact_kind",
        "artifact_semantics",
        "record_count",
        "total_bytes",
        "content_hash",
        "hash_algorithm",
        "execution_fingerprint",
        "input_snapshot_count",
        "input_snapshot_ids",
        "input_snapshot_content_hashes",
        "pipeline_name",
        "provider",
        "entity",
        "run_id",
        "manifest_id",
    )
    return {
        key: artifact_ref[key]
        for key in ordered_keys
        if key in artifact_ref and artifact_ref[key] is not None
    }


def build_produced_artifact_trace(
    *,
    manifest: RunManifest,
    ledger_entries_present: bool,
    artifact_refs: list[dict[str, object]],
) -> dict[str, object]:
    """Return the manifest-id rooted concrete produced-artifact trace."""
    artifacts = [
        build_trace_artifact_ref(artifact_ref)
        for artifact_ref in sorted(artifact_refs, key=artifact_ref_sort_key)
    ]
    missing_requirements: list[str] = []
    if not ledger_entries_present:
        missing_requirements.append("run_ledger_history")
    if not artifacts:
        missing_requirements.append("artifact_publication_event")
    return {
        "lookup": "run_ledger_by_manifest_id",
        "lookup_key": manifest.manifest_id,
        "manifest_id": manifest.manifest_id,
        "complete": not missing_requirements,
        "artifact_count": len(artifacts),
        "artifacts": artifacts,
        "missing_requirements": missing_requirements,
    }
