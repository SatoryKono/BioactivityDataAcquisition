"""Shared JSON payload helpers for historical replay inventory rows."""

from __future__ import annotations

from bioetl.application.services.control_plane.replay.historical_identity_models import (
    HistoricalReplayRunIdentity,
    build_historical_identity_core_payload,
)


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


def build_historical_certification_payload(
    *,
    certification_status: str,
    replay_occurrence_kind: str,
    blocking_reasons: tuple[str, ...] = (),
) -> dict[str, object]:
    """Return common certification fields shared by historical replay rows."""
    return {
        "certification_status": certification_status,
        "replay_occurrence_kind": replay_occurrence_kind,
        "blocking_reasons": blocking_reasons,
    }


def build_historical_certified_identity_payload(
    identity: HistoricalReplayRunIdentity,
    *,
    certification_status: str,
    replay_occurrence_kind: str,
    blocking_reasons: tuple[str, ...] = (),
    **extra_fields: object,
) -> dict[str, object]:
    """Return one JSON-safe historical replay row with shared identity anchors."""
    return build_historical_run_identity_payload(
        **build_historical_identity_core_payload(identity),
        **build_historical_certification_payload(
            certification_status=certification_status,
            replay_occurrence_kind=replay_occurrence_kind,
            blocking_reasons=blocking_reasons,
        ),
        **extra_fields,
    )


def build_historical_certified_identity_payload_from_record(
    record: object,
    **extra_fields: object,
) -> dict[str, object]:
    """Build one historical replay row from a record exposing certification fields."""
    return build_historical_certified_identity_payload(
        record,
        certification_status=str(record.certification_status),
        replay_occurrence_kind=str(record.replay_occurrence_kind),
        blocking_reasons=tuple(getattr(record, "blocking_reasons", ())),
        **extra_fields,
    )


__all__ = [
    "build_historical_certification_payload",
    "build_historical_certified_identity_payload",
    "build_historical_certified_identity_payload_from_record",
    "build_historical_run_identity_payload",
]
