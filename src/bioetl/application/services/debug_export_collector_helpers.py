"""Shared row helpers for debug export collectors."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from datetime import datetime

from bioetl.domain.types import BronzeRecord

from .debug_export_helpers import (
    _base_row,
    _lineage_sort_key,
    _normalize_optional_text,
    _payload_hash,
    _primary_key,
    _source_record_id,
)


def build_dq_summary_rows(
    *,
    run_id: str,
    workflow_id: str,
    pipeline_id: str,
    silver_rejected_rows: Sequence[dict[str, object]],
    silver_quarantine_rows: Sequence[dict[str, object]],
    gold_rejected_rows: Sequence[dict[str, object]],
) -> tuple[dict[str, object], ...]:
    """Build deterministic DQ summary rows from collected exclusion tables."""
    counter = Counter()
    for rows in (
        silver_rejected_rows,
        silver_quarantine_rows,
        gold_rejected_rows,
    ):
        for row in rows:
            counter[
                (
                    row.get("stage", ""),
                    row.get("status", ""),
                    row.get("reason_code", ""),
                    row.get("action", ""),
                )
            ] += 1
    return tuple(
        {
            "run_id": run_id,
            "workflow_id": workflow_id,
            "pipeline_id": pipeline_id,
            "stage": stage,
            "status": status,
            "reason_code": reason_code,
            "action": action,
            "record_count": count,
        }
        for (stage, status, reason_code, action), count in sorted(counter.items())
    )


def get_sorted_lineage_rows(
    rows: Sequence[dict[str, object]],
) -> tuple[dict[str, object], ...]:
    """Return lineage rows sorted by stable fragment/edge/node identity."""
    return tuple(sorted(rows, key=_lineage_sort_key))


def source_metadata_attrs(source_metadata: object | None) -> dict[str, object]:
    """Return JSON-like source metadata attributes from supported object shapes."""
    if isinstance(source_metadata, dict):
        return dict(source_metadata)
    if hasattr(source_metadata, "model_dump"):
        return source_metadata.model_dump()
    if hasattr(source_metadata, "__dict__"):
        return source_metadata.__dict__
    return {}


def resolve_debug_record_index(record: Mapping[str, object]) -> int | None:
    """Resolve an optional debug record index from a row payload."""
    existing = _normalize_optional_text(record.get("_debug_record_index"))
    try:
        return int(existing) if existing else None
    except ValueError:
        return None


def build_gold_rejected_row(
    *,
    run_id: str,
    workflow_id: str,
    pipeline_id: str,
    provider_id: str,
    record_index: int | None,
    normalized_record: Mapping[str, object],
    created_at: datetime,
    action: str,
    reason_code: str,
    reason_message: str,
    rule_id: str,
    failed_field: str,
) -> dict[str, object]:
    """Build one canonical Gold rejection row."""
    return _base_row(
        run_id=run_id,
        workflow_id=workflow_id,
        pipeline_id=pipeline_id,
        provider_id=provider_id,
        stage="gold",
        record_index=record_index,
        raw_record=normalized_record,
        normalized_record=normalized_record,
        status="rejected",
        action=action,
        created_at=created_at,
        reason_code=reason_code,
        reason_message=reason_message,
        rule_id=rule_id,
        rule_layer="gold",
        failed_field=failed_field,
    )


def build_lineage_row(
    *,
    run_id: str,
    workflow_id: str,
    pipeline_id: str,
    provider_id: str,
    fragment_id: str,
    edge_type: str,
    node_id: str,
    raw_record: BronzeRecord,
    created_at: datetime,
) -> dict[str, object]:
    """Build one deterministic debug lineage row."""
    return {
        "run_id": run_id,
        "workflow_id": workflow_id,
        "pipeline_id": pipeline_id,
        "provider_id": provider_id,
        "fragment_id": fragment_id,
        "edge_type": edge_type,
        "node_id": node_id,
        "primary_key": _primary_key(raw_record),
        "payload_hash": _payload_hash(provider_id=provider_id, record=raw_record),
        "source_record_id": _source_record_id(raw_record),
        "created_at": created_at.isoformat(),
    }


__all__ = [
    "build_dq_summary_rows",
    "build_gold_rejected_row",
    "build_lineage_row",
    "get_sorted_lineage_rows",
    "resolve_debug_record_index",
    "source_metadata_attrs",
]
