"""Shared artifact payload fields for run-manifest diagnostics."""

from __future__ import annotations

from collections.abc import Mapping

from bioetl.domain.control_plane import RunLedgerEntry

ARTIFACT_DETAIL_KEYS = (
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

ARTIFACT_TRACE_ORDERED_KEYS = (
    "event_type",
    "publication_status",
    "stage",
    "artifact_id",
    "dataset_ref",
    "lineage_fragment_id",
    "artifact_path",
    *ARTIFACT_DETAIL_KEYS,
)


def build_artifact_ref_from_ledger_entry(
    entry: RunLedgerEntry,
) -> dict[str, object] | None:
    """Return one artifact reference emitted from a ledger entry."""
    if entry.event_family != "artifact" and entry.event_type != "artifact_published":
        return None
    details = entry.details if isinstance(entry.details, Mapping) else {}
    artifact_path = details.get("artifact_path")
    artifact_ref: dict[str, object] = {
        "event_type": entry.event_type,
        "publication_status": entry.status,
        "stage": entry.stage,
        "artifact_id": entry.dataset_ref,
        "dataset_ref": entry.dataset_ref,
        "lineage_fragment_id": entry.lineage_fragment_id,
        "artifact_path": None if artifact_path is None else str(artifact_path),
    }
    for detail_key in ARTIFACT_DETAIL_KEYS:
        detail_value = details.get(detail_key)
        if detail_value is not None:
            artifact_ref[detail_key] = detail_value
    return artifact_ref
