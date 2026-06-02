"""Helper functions for debug export service."""

from collections.abc import Mapping
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from bioetl.domain.behavior.identity_service import EntityIdentityGenerator
from bioetl.domain.types import ErrorType

if TYPE_CHECKING:
    pass

_SOURCE_ID_FIELDS = (
    "activity_id",
    "document_chembl_id",
    "publication_id",
    "molecule_chembl_id",
    "target_chembl_id",
    "assay_chembl_id",
    "chembl_id",
    "id",
    "entity_id",
)


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _normalize_text(value: object | None) -> str:
    if value is None:
        return ""
    return str(value)


def _normalize_optional_text(value: object | None) -> str | None:
    text = _normalize_text(value).strip()
    return text or None


def _safe_payload(record: Mapping[str, object] | None) -> dict[str, object]:
    return {} if record is None else dict(record)


def _jsonable_payload(payload: Mapping[str, object] | None) -> str:
    import json

    return json.dumps(_safe_payload(payload), ensure_ascii=False, sort_keys=True)


def _primary_key(record: Mapping[str, object] | None) -> str:
    payload = _safe_payload(record)
    entity_id = _normalize_optional_text(payload.get("entity_id"))
    if entity_id is not None:
        return entity_id
    source_id = _source_record_id(payload)
    return source_id or ""


def _source_record_id(record: Mapping[str, object] | None) -> str:
    payload = _safe_payload(record)
    for field_name in _SOURCE_ID_FIELDS:
        value = _normalize_optional_text(payload.get(field_name))
        if value is not None:
            return value
    return ""


def _infer_failed_field(record: Mapping[str, object], details: str) -> str:
    lowered = details.lower()
    for field_name in sorted(record):
        if field_name.lower() in lowered:
            return field_name
    return ""


def _extract_rule_id(details: str) -> str:
    if "rules=[" not in details:
        return ""
    _, _, tail = details.partition("rules=[")
    value, _, _ = tail.partition("]")
    return value.strip()


def _infer_reason_code(
    *,
    error_type: ErrorType | None = None,
    details: str = "",
    policy: str | None = None,
) -> str:
    normalized = details.lower()
    if "missing" in normalized and (
        "field" in normalized or "_" in normalized or ":" in normalized
    ):
        return "SCHEMA_REQUIRED_FIELD_MISSING"
    if "schema" in normalized or (
        error_type is not None and error_type.value == "schema_violation"
    ):
        return "SCHEMA_TYPE_MISMATCH"
    if "runtime dq validation failed" in normalized:
        return "DQ_HARD_RULE_FAILED"
    if policy == "quarantine":
        return "QUARANTINE_POLICY"
    return "DQ_SOFT_RULE_FAILED"


def _payload_hash(
    *,
    provider_id: str,
    record: Mapping[str, object] | None,
) -> str:
    payload = _safe_payload(record)
    if not payload:
        return ""
    existing = _normalize_optional_text(payload.get("content_hash"))
    if existing is not None:
        return existing
    generator = EntityIdentityGenerator()
    return generator.generate_identity(payload, provider_id)


def _row_sort_key(row: Mapping[str, object]) -> tuple[int | None, str, str]:
    index_value = row.get("record_index")
    try:
        record_index = int(index_value) if index_value is not None else None
    except (TypeError, ValueError):
        record_index = None
    return (
        record_index,
        _normalize_text(row.get("primary_key")),
        _normalize_text(row.get("payload_hash")),
    )


def _lineage_sort_key(row: Mapping[str, object]) -> tuple[str, str, str]:
    return (
        _normalize_text(row.get("fragment_id")),
        _normalize_text(row.get("edge_type")),
        _normalize_text(row.get("node_id")),
    )


def _base_row(
    *,
    run_id: str,
    workflow_id: str,
    pipeline_id: str,
    provider_id: str,
    stage: str,
    record_index: int | None,
    raw_record: Mapping[str, object] | None,
    normalized_record: Mapping[str, object] | None,
    status: str,
    created_at: datetime,
    action: str = "",
    reason_code: str = "",
    reason_message: str = "",
    rule_id: str = "",
    rule_layer: str = "",
    failed_field: str = "",
    failed_value: str = "",
    expected_constraint: str = "",
) -> dict[str, object]:
    return {
        "run_id": run_id,
        "workflow_id": workflow_id,
        "pipeline_id": pipeline_id,
        "provider_id": provider_id,
        "stage": stage,
        "record_index": record_index,
        "source_record_id": _source_record_id(raw_record or normalized_record),
        "primary_key": _primary_key(normalized_record or raw_record),
        "payload_hash": _payload_hash(
            provider_id=provider_id, record=normalized_record or raw_record
        ),
        "input_payload_hash": _payload_hash(provider_id=provider_id, record=raw_record),
        "output_payload_hash": _payload_hash(
            provider_id=provider_id, record=normalized_record
        ),
        "status": status,
        "reason_code": reason_code,
        "reason_message": reason_message,
        "rule_id": rule_id,
        "rule_layer": rule_layer,
        "failed_field": failed_field,
        "failed_value": failed_value,
        "expected_constraint": expected_constraint,
        "action": action,
        "created_at": created_at.isoformat(),
        "raw_payload": _jsonable_payload(raw_record),
        "normalized_payload": _jsonable_payload(normalized_record),
    }
