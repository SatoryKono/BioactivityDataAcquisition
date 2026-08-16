"""Ledger-derived input-snapshot normalization for manifest diagnostics."""

from __future__ import annotations

from collections.abc import Mapping

from bioetl.application.services.control_plane.replay._historical_snapshot_materialization_modes import (
    LIVE_CAPTURE_SNAPSHOT_MATERIALIZED,
)
from bioetl.domain.control_plane import RunLedgerEntry
from bioetl.domain.control_plane.run_ledger import INPUT_SNAPSHOT_PUBLISHED_EVENT


def collect_ledger_input_snapshot_refs(
    ledger_entries: tuple[RunLedgerEntry, ...],
) -> list[dict[str, object]]:
    """Return input snapshots materialized after manifest creation via ledger."""
    refs: dict[str, dict[str, object]] = {}
    for entry in ledger_entries:
        if entry.event_type != INPUT_SNAPSHOT_PUBLISHED_EVENT:
            continue
        details = entry.details if isinstance(entry.details, Mapping) else {}
        snapshot_id = _snapshot_required_text(details.get("snapshot_id"))
        content_hash = _snapshot_required_text(details.get("content_hash"))
        immutable_uri = _snapshot_required_text(details.get("immutable_uri"))
        if snapshot_id is None or content_hash is None or immutable_uri is None:
            continue
        refs[snapshot_id] = {
            "provider": _snapshot_required_text(details.get("provider")),
            "entity": _snapshot_required_text(details.get("entity")),
            "pipeline_name": _snapshot_required_text(details.get("pipeline_name")),
            "query": _snapshot_required_text(details.get("query")),
            "snapshot_id": snapshot_id,
            "content_hash": content_hash,
            "immutable_uri": immutable_uri,
            "query_fingerprint": _snapshot_required_text(
                details.get("query_fingerprint")
            ),
            "storage_provider": _snapshot_required_text(
                details.get("storage_provider")
            ),
            "object_bucket": _snapshot_required_text(details.get("object_bucket")),
            "object_key": _snapshot_required_text(details.get("object_key")),
            "object_version_id": _snapshot_required_text(
                details.get("object_version_id")
            ),
            "etag": _snapshot_required_text(details.get("etag")),
            "last_modified": _snapshot_required_text(details.get("last_modified")),
            "captured_at": _snapshot_required_text(details.get("captured_at")),
            "materialization_mode": _snapshot_required_text(
                details.get("materialization_mode")
            )
            or LIVE_CAPTURE_SNAPSHOT_MATERIALIZED,
            "certification_scope": _snapshot_required_text(
                details.get("certification_scope")
            ),
            "certification_basis": _snapshot_required_text(
                details.get("certification_basis")
            ),
            "certification_artifact_ref": _snapshot_required_text(
                details.get("certification_artifact_ref")
            ),
            "upstream_run_id": _snapshot_required_text(details.get("upstream_run_id")),
            "upstream_manifest_id": _snapshot_required_text(
                details.get("upstream_manifest_id")
            ),
            "source_event_id": entry.entry_id,
        }
    return [refs[key] for key in sorted(refs)]


def _snapshot_required_text(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


__all__ = ["collect_ledger_input_snapshot_refs"]
