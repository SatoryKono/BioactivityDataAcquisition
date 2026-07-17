"""Ledger and artifact extraction helpers for Control Plane identity.

Legacy HTTP contract compatibility layer - sunset date: 2026-12-31
This module extracts legacy HTTP identity anchor values.
"""

from __future__ import annotations

from bioetl.domain.control_plane import RunLedgerEntry, RunManifest
from bioetl.domain.control_plane.run_ledger import (
    COMPOSITE_DEPENDENCY_COMPLETED_EVENT,
    COMPOSITE_ENRICHER_COMPLETED_EVENT,
    COMPOSITE_MERGE_COMPLETED_EVENT,
)
from bioetl.interfaces.http.control_plane_identity.checkpoint_extractors import (
    first_payload_value,
)
from bioetl.interfaces.http.control_plane_identity.formatting import (
    append_value,
    dedupe,
)
from bioetl.interfaces.http.control_plane_identity.manifest_extractors import (
    artifact_ref_values,
    input_snapshots,
)
from bioetl.interfaces.http.control_plane_identity.types import AnchorValues

_COMPOSITE_EVENTS = frozenset(
    {
        COMPOSITE_DEPENDENCY_COMPLETED_EVENT,
        COMPOSITE_ENRICHER_COMPLETED_EVENT,
        COMPOSITE_MERGE_COMPLETED_EVENT,
    }
)


def artifact_refs(
    manifest: RunManifest,
    ledger_entries: tuple[RunLedgerEntry, ...],
) -> list[str]:
    values = published_artifacts(ledger_entries)
    return values or artifact_ref_values(manifest.planned_artifacts)


def published_artifacts(ledger_entries: tuple[RunLedgerEntry, ...]) -> list[str]:
    values: list[str] = []
    for entry in ledger_entries:
        details = entry.details or {}
        for key in ("artifact_ref", "artifact_path", "path", "uri"):
            append_value(values, details.get(key))
    return dedupe(values)


def lineage_fragment_ids(ledger_entries: tuple[RunLedgerEntry, ...]) -> list[str]:
    return dedupe(
        [
            entry.lineage_fragment_id
            for entry in ledger_entries
            if entry.lineage_fragment_id
        ]
    )


def component_run_ids(ledger_entries: tuple[RunLedgerEntry, ...]) -> list[str]:
    values: list[str] = []
    for entry in ledger_entries:
        if entry.event_type not in _COMPOSITE_EVENTS:
            continue
        details = entry.details or {}
        for key in ("component_run_id", "child_run_id", "upstream_run_id", "run_id"):
            append_value(values, details.get(key))
        append_value(values, details.get("component_run_ids"))
    return dedupe(values)


def dq_report_paths(
    manifest: RunManifest,
    ledger_entries: tuple[RunLedgerEntry, ...],
) -> list[str]:
    values: list[str] = []
    append_value(
        values, first_payload_value(manifest, "dq_report_paths", "dq_report_path")
    )
    for entry in ledger_entries:
        details = entry.details or {}
        append_value(values, details.get("dq_report_paths"))
        append_value(values, details.get("dq_report_path"))
    return dedupe(values)


def bronze_batch_ids(
    manifest: RunManifest,
    ledger_entries: tuple[RunLedgerEntry, ...],
) -> list[str]:
    values = [item.snapshot_id for item in input_snapshots(manifest)]
    for entry in ledger_entries:
        details = entry.details or {}
        for key in ("bronze_batch_id", "bronze_batch_ids", "source_batch_ids"):
            append_value(values, details.get(key))
    return dedupe(values)


def extract_ledger_anchors(ledger_event: dict[str, object]) -> list[AnchorValues]:
    """Extract legacy HTTP identity anchor values from ledger-event mappings."""
    from bioetl.interfaces.http.control_plane_identity.anchor_values import (
        anchor_values_from_mapping,
    )

    return anchor_values_from_mapping(
        ledger_event,
        source="ledger",
        anchor_names=("run_id", "manifest_id", "latest_event_id"),
    )


__all__ = [
    "artifact_refs",
    "bronze_batch_ids",
    "component_run_ids",
    "dq_report_paths",
    "extract_ledger_anchors",
    "lineage_fragment_ids",
    "published_artifacts",
]
