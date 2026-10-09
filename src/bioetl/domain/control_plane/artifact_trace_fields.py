"""Canonical ordered fields for published-artifact trace payloads."""

from __future__ import annotations

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

__all__ = ["ARTIFACT_DETAIL_KEYS", "ARTIFACT_TRACE_ORDERED_KEYS"]
