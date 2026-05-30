"""Shared JSON payload helpers for historical replay inventory rows."""

from __future__ import annotations


def build_historical_run_identity_payload(
    *,
    manifest_id: str,
    run_id: str,
    pipeline_name: str,
    provider: str,
    entity: str,
    execution_context: str,
    certification_status: str,
    replay_occurrence_kind: str,
    blocking_reasons: tuple[str, ...] = (),
    **extra_fields: object,
) -> dict[str, object]:
    """Return one JSON-safe historical run identity payload."""
    payload: dict[str, object] = {
        "manifest_id": manifest_id,
        "run_id": run_id,
        "pipeline_name": pipeline_name,
        "provider": provider,
        "entity": entity,
        "execution_context": execution_context,
        "certification_status": certification_status,
        "replay_occurrence_kind": replay_occurrence_kind,
        "blocking_reasons": list(blocking_reasons),
    }
    payload.update(extra_fields)
    return payload


__all__ = ["build_historical_run_identity_payload"]
