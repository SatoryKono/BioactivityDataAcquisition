"""Helpers for bounded rich run-ledger event payloads."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol

from bioetl.domain.control_plane import RunLedgerEntry
from bioetl.domain.control_plane.run_ledger import (
    COMPOSITE_DEPENDENCY_COMPLETED_EVENT,
    COMPOSITE_ENRICHER_COMPLETED_EVENT,
    COMPOSITE_MERGE_COMPLETED_EVENT,
    INPUT_SNAPSHOT_PUBLISHED_EVENT,
)

__all__ = [
    "record_composite_dependency_completed",
    "record_composite_enricher_completed",
    "record_composite_merge_completed",
    "record_input_snapshot_published",
]


class _RunLedgerAppender(Protocol):
    def _append(
        self,
        *,
        event_type: str,
        status: str | None,
        stage: str | None = None,
        details: dict[str, object] | None = None,
    ) -> RunLedgerEntry: ...


def _required_text(value: object, field_name: str) -> str:
    """Return a normalized required text value for bounded ledger payloads."""
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"{field_name} is required")
    return text


def record_composite_dependency_completed(
    appender: _RunLedgerAppender,
    *,
    dependency_name: str,
    result: Mapping[str, object],
) -> RunLedgerEntry:
    """Record bounded dependency result evidence for rich composite replay."""
    payload = dict(result)
    payload["dependency_name"] = _required_text(dependency_name, "dependency_name")
    payload["pipeline_name"] = _required_text(
        payload.get("pipeline_name") or dependency_name,
        "pipeline_name",
    )
    return appender._append(
        event_type=COMPOSITE_DEPENDENCY_COMPLETED_EVENT,
        status=str(payload.get("status", "completed")),
        stage="dependencies",
        details=payload,
    )


def record_composite_enricher_completed(
    appender: _RunLedgerAppender,
    *,
    enricher_name: str,
    result: Mapping[str, object],
) -> RunLedgerEntry:
    """Record bounded enricher result evidence for rich composite replay."""
    payload = dict(result)
    payload["enricher_name"] = _required_text(enricher_name, "enricher_name")
    return appender._append(
        event_type=COMPOSITE_ENRICHER_COMPLETED_EVENT,
        status=str(payload.get("status", "completed")),
        stage="enrichment",
        details=payload,
    )


def record_composite_merge_completed(
    appender: _RunLedgerAppender,
    *,
    result: Mapping[str, object],
) -> RunLedgerEntry:
    """Record bounded merge result evidence for rich composite replay."""
    return appender._append(
        event_type=COMPOSITE_MERGE_COMPLETED_EVENT,
        status="completed",
        stage="merge",
        details=dict(result),
    )


def record_input_snapshot_published(
    appender: _RunLedgerAppender,
    *,
    provider: str,
    entity: str,
    pipeline_name: str,
    snapshot_id: str,
    content_hash: str,
    immutable_uri: str,
    bronze_batch_ref: str,
    query_fingerprint: str | None = None,
    details: Mapping[str, object] | None = None,
) -> RunLedgerEntry:
    """Record immutable input snapshot evidence published after Bronze write."""
    payload: dict[str, object] = {
        "provider": _required_text(provider, "provider"),
        "entity": _required_text(entity, "entity"),
        "pipeline_name": _required_text(pipeline_name, "pipeline_name"),
        "snapshot_id": _required_text(snapshot_id, "snapshot_id"),
        "content_hash": _required_text(content_hash, "content_hash"),
        "immutable_uri": _required_text(immutable_uri, "immutable_uri"),
        "bronze_batch_ref": _required_text(bronze_batch_ref, "bronze_batch_ref"),
    }
    if query_fingerprint is not None:
        payload["query_fingerprint"] = str(query_fingerprint)
    if details:
        payload.update(dict(details))
    return appender._append(
        event_type=INPUT_SNAPSHOT_PUBLISHED_EVENT,
        status="published",
        stage="bronze",
        details=payload,
    )
