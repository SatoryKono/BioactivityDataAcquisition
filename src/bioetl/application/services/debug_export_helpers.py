"""Helper functions for debug export service."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, date, datetime
from pathlib import Path
from uuid import UUID

from bioetl.domain.behavior.identity_service import EntityIdentityGenerator
from bioetl.domain.types import ErrorType

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


def _record_payload(record: object | None) -> dict[str, object]:
    if record is None:
        return {}
    if isinstance(record, Mapping):
        return dict(record)
    model_dump = getattr(record, "model_dump", None)
    if callable(model_dump):
        payload = model_dump()
        if isinstance(payload, Mapping):
            return dict(payload)
    record_dict = getattr(record, "__dict__", None)
    if isinstance(record_dict, Mapping):
        return dict(record_dict)
    return {}


def _safe_payload(record: object | None) -> dict[str, object]:
    return _record_payload(record)


def _jsonable_payload(payload: object | None) -> str:
    import json

    return json.dumps(
        _safe_payload(payload),
        ensure_ascii=False,
        sort_keys=True,
        default=_json_default,
    )


def _jsonable_value(value: object | None) -> str:
    import json

    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        default=_json_default,
    )


def _json_default(value: object) -> str:
    if isinstance(value, datetime | date):
        return value.isoformat()
    if isinstance(value, Path | UUID):
        return str(value)
    return str(value)


def _primary_key(record: object | None) -> str:
    payload = _safe_payload(record)
    entity_id = _normalize_optional_text(payload.get("entity_id"))
    if entity_id is not None:
        return entity_id
    source_id = _source_record_id(payload)
    return source_id or ""


def _source_record_id(record: object | None) -> str:
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


def _extract_rejection_details_mapping(
    details: object | None,
) -> dict[str, object] | None:
    if details is None:
        return None
    if isinstance(details, Mapping):
        return dict(details)
    model_dump = getattr(details, "model_dump", None)
    if callable(model_dump):
        payload = model_dump()
        if isinstance(payload, Mapping):
            return dict(payload)
    record_dict = getattr(details, "__dict__", None)
    if isinstance(record_dict, Mapping):
        return dict(record_dict)
    return None


def _extract_expected_constraint_from_details(details: Mapping[str, object]) -> str:
    operator = _normalize_optional_text(details.get("operator"))
    if "expected" in details:
        expected = details.get("expected")
        if expected is None:
            expected_text = "None"
        elif isinstance(expected, str | int | float | bool):
            expected_text = str(expected)
        else:
            expected_text = _jsonable_value(expected)
        if operator is None:
            return expected_text
        return f"{operator} {expected_text}".strip()

    for key in ("constraint", "check"):
        value = _normalize_optional_text(details.get(key))
        if value is not None:
            return value
    return ""


def _extract_rejection_diagnostics(
    *,
    record: Mapping[str, object],
    details: object | None,
    message: str,
) -> tuple[str, str, str]:
    detail_mapping = _extract_rejection_details_mapping(details)
    if detail_mapping is None:
        return _infer_failed_field(record, message), "", ""

    failed_field = _normalize_optional_text(detail_mapping.get("field"))
    if failed_field is None:
        failed_field = _infer_failed_field(record, message)

    failed_value = ""
    if "actual" in detail_mapping:
        actual = detail_mapping.get("actual")
        if actual is None:
            failed_value = "None"
        elif isinstance(actual, str | int | float | bool):
            failed_value = str(actual)
        else:
            failed_value = _jsonable_value(actual)
    elif failed_field and failed_field in record:
        actual = record.get(failed_field)
        if actual is None:
            failed_value = "None"
        elif isinstance(actual, str | int | float | bool):
            failed_value = str(actual)
        else:
            failed_value = _jsonable_value(actual)

    expected_constraint = _extract_expected_constraint_from_details(detail_mapping)
    return failed_field, failed_value, expected_constraint


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
    record: object | None,
) -> str:
    payload = _safe_payload(record)
    if not payload:
        return ""
    existing = _normalize_optional_text(payload.get("content_hash"))
    if existing is not None:
        return existing
    generator = EntityIdentityGenerator()
    return generator.compute_content_hash(provider_id, payload)


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
