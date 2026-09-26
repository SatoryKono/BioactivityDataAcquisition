"""Canonical event payload helpers for file audit logging."""

from __future__ import annotations

from datetime import datetime

from bioetl.domain.observability_contract import build_observability_contract_payload
from bioetl.domain.types import JsonDict

CANONICAL_AUDIT_OPTIONAL_FIELDS = (
    "manifest_id",
    "composite_run_id",
    "entity",
    "phase",
    "status",
)
AUDIT_EVENT_NAME_TO_CANONICAL = {
    "PipelineRunStarted": "pipeline_started",
    "PipelineRunCompleted": "pipeline_finished",
    "PipelineRunFailed": "pipeline_failed",
    "PipelineRunShutdown": "pipeline_shutdown",
}


def coerce_text(value: object, *, fallback: str) -> str:
    text = str(value).strip() if value is not None else ""
    return text or fallback


def default_severity(event_data: JsonDict) -> str:
    severity = event_data.get("severity")
    if severity is not None:
        return coerce_text(severity, fallback="info")
    status = coerce_text(event_data.get("status"), fallback="")
    if status in {"failed", "failure", "error"}:
        return "error"
    if status in {"warning", "degraded"}:
        return "warning"
    return "info"


def build_canonical_event_payload(
    *,
    event_name: str,
    event_data: JsonDict | None,
    timestamp: datetime,
) -> JsonDict:
    raw_event_data = dict(event_data or {})
    canonical_context = dict(raw_event_data)
    canonical_context.setdefault(
        "event",
        AUDIT_EVENT_NAME_TO_CANONICAL.get(event_name, event_name),
    )
    canonical = build_observability_contract_payload(
        event_name=event_name,
        context=canonical_context,
        default_provider=coerce_text(
            raw_event_data.get("provider"), fallback="unknown"
        ),
        default_pipeline=coerce_text(
            raw_event_data.get("pipeline") or raw_event_data.get("pipeline_name"),
            fallback="unknown",
        ),
        default_run_id=coerce_text(raw_event_data.get("run_id"), fallback="unknown"),
        default_severity=default_severity(raw_event_data),
    ).context
    payload: JsonDict = dict(canonical)
    payload["recorded_at"] = timestamp.isoformat()
    payload["context"] = dict(canonical)
    payload["event_name"] = event_name
    payload["event_data"] = raw_event_data
    payload["timestamp"] = payload["recorded_at"]
    for field in CANONICAL_AUDIT_OPTIONAL_FIELDS:
        if field in canonical and canonical[field] is not None:
            payload[field] = canonical[field]
    return payload
