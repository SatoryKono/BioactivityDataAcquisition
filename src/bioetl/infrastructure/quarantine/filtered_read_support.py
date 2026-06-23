"""Pure helper functions for quarantine filtered-row normalization and filtering."""

from __future__ import annotations

from datetime import UTC, datetime

from bioetl.domain.serialization import deserialize_from_json
from bioetl.domain.types import JsonDict

__all__ = [
    "_build_payload_preview",
    "_build_reason_field_signature",
    "_build_reason_signature",
    "_clamp_limit",
    "_collect_string_field_values",
    "_increment_counter",
    "_iter_filtered_rows",
    "_normalize_error_details",
    "_normalize_filter_values",
    "_normalize_filtered_row",
    "_normalize_timestamp",
    "_single_filter_value",
]


def _normalize_error_details(record: JsonDict) -> JsonDict:
    """Return structured error details for one quarantine row."""
    error_details = record.get("error_details")
    if isinstance(error_details, str):
        decoded = deserialize_from_json(error_details)
        if isinstance(decoded, dict):
            return decoded
        return {}
    if isinstance(error_details, dict):
        return error_details
    return {}


def _increment_counter(counter: dict[str, int], value: object) -> None:
    """Increment a string-keyed counter when the value is populated."""
    if not isinstance(value, str):
        return
    normalized = value.strip()
    if not normalized:
        return
    counter[normalized] = counter.get(normalized, 0) + 1


def _build_reason_signature(error_details: JsonDict) -> str | None:
    """Build a stable aggregation key for one structured Silver filter reason."""
    parts: list[str] = []
    for key in ("reason_code", "rule_type", "field", "operator"):
        value = error_details.get(key)
        if isinstance(value, str) and value.strip():
            parts.append(value.strip())
    if not parts:
        return None
    return " | ".join(parts)


def _build_reason_field_signature(error_details: JsonDict) -> str | None:
    """Build a stable reason+field grouping key for operator summaries."""
    parts: list[str] = []
    for key in ("reason_code", "field"):
        value = error_details.get(key)
        if isinstance(value, str) and value.strip():
            parts.append(value.strip())
    if not parts:
        return None
    return " | ".join(parts)


def _normalize_timestamp(value: object) -> tuple[str, datetime | None]:
    """Return an ISO timestamp string and parsed datetime when possible."""
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=UTC)
        return value.isoformat(), value
    if not isinstance(value, str):
        return "", None
    normalized = value.strip()
    if not normalized:
        return "", None
    try:
        parsed = datetime.fromisoformat(normalized.replace("Z", "+00:00"))
    except ValueError:
        return normalized, None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return normalized, parsed


def _build_payload_preview(payload: object) -> JsonDict:
    """Build a compact payload preview for table rendering."""
    if isinstance(payload, dict):
        keys = list(payload.keys())
        preview: JsonDict = {key: payload[key] for key in keys[:8]}
        if len(keys) > 8:
            preview["_truncated_keys"] = len(keys) - 8
        return preview
    return {"value": payload}


def _extract_run_type(record: JsonDict, error_details: JsonDict) -> str:
    """Resolve run_type from structured fields if available."""
    for source in (
        error_details.get("run_type"),
        error_details.get("_run_type"),
        record.get("run_type"),
        record.get("_run_type"),
    ):
        if isinstance(source, str) and source.strip():
            return source.strip()
    return ""


def _normalize_filtered_row(
    record: JsonDict,
    *,
    run_type_lookup: dict[str, str] | None,
    include_payload: bool,
    include_payload_preview: bool,
) -> JsonDict:
    """Normalize one Silver-filter quarantine row for explorer responses."""
    error_details = _normalize_error_details(record)
    ingestion_ts_raw, _ = _normalize_timestamp(record.get("ingestion_ts"))

    reason_message = error_details.get("message")
    reason = (
        reason_message.strip()
        if isinstance(reason_message, str) and reason_message.strip()
        else record.get("error_code", "")
    )

    extracted_run_type = _extract_run_type(record, error_details)
    if not extracted_run_type and run_type_lookup is not None:
        run_id_value = record.get("run_id")
        if isinstance(run_id_value, str):
            extracted_run_type = run_type_lookup.get(run_id_value.strip(), "")

    normalized: JsonDict = {
        "ingestion_ts": ingestion_ts_raw,
        "pipeline": record.get("pipeline", ""),
        "run_id": record.get("run_id", ""),
        "run_type": extracted_run_type,
        "payload_hash": record.get("payload_hash", ""),
        "reason_code": error_details.get("reason_code", ""),
        "rule_type": error_details.get("rule_type", ""),
        "field": error_details.get("field", ""),
        "operator": error_details.get("operator", ""),
        "expected": error_details.get("expected"),
        "actual": error_details.get("actual"),
        "dq_status": record.get("dq_status", ""),
        "reason": reason,
    }
    if include_payload_preview or include_payload:
        payload_raw = record.get("payload")
        payload = (
            deserialize_from_json(payload_raw)
            if isinstance(payload_raw, str)
            else payload_raw
        )
        if not isinstance(payload, dict):
            payload = {"value": payload}
        normalized["payload_preview"] = _build_payload_preview(payload)
    if include_payload:
        normalized["payload"] = payload
    return normalized


def _normalize_filter_values(raw: str | None) -> set[str] | None:
    """Parse comma-separated filter values into a normalized set."""
    if raw is None:
        return None
    candidate = raw.strip()
    if not candidate:
        return None
    wildcard_tokens = {"*", "all", "__all", "$__all", "$all", ".*"}
    if candidate.lower() in wildcard_tokens:
        return None

    values: set[str] = set()
    for item in candidate.split(","):
        normalized = item.strip()
        if not normalized:
            continue
        if normalized.lower() in wildcard_tokens:
            continue
        values.add(normalized)
    return values or None


def _matches_values_filter(value: object, allowed: set[str] | None) -> bool:
    """Return True when value passes an optional set-membership filter."""
    if allowed is None:
        return True
    if not isinstance(value, str):
        return False
    return value.strip() in allowed


def _single_filter_value(raw: str | None) -> str | None:
    """Return one normalized value when filter resolves to exactly one item."""
    values = _normalize_filter_values(raw)
    if values is None or len(values) != 1:
        return None
    return next(iter(values))


def _collect_string_field_values(
    rows: list[JsonDict],
    field_name: str,
) -> list[str]:
    """Collect unique non-empty string values for one normalized row field."""
    values = {
        value.strip()
        for row in rows
        if isinstance((value := row.get(field_name)), str) and value.strip()
    }
    return sorted(values)


def _parse_time_bound(value: str | None) -> datetime | None:
    """Parse one optional ISO-8601 time bound."""
    if value is None:
        return None
    candidate = value.strip()
    if not candidate:
        return None
    try:
        parsed = datetime.fromisoformat(candidate.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed


def _clamp_limit(limit: int, *, default: int = 50, hard_cap: int = 500) -> int:
    """Clamp list-query limit to a safe range."""
    if limit <= 0:
        return default
    return min(limit, hard_cap)


def _row_matches_filters(
    row: JsonDict,
    *,
    pipeline_filter: set[str] | None,
    run_type_filter: set[str] | None,
    reason_code_filter: set[str] | None,
    field_filter: set[str] | None,
    run_id_filter: set[str] | None,
    payload_hash_filter: set[str] | None,
) -> bool:
    """Return True when a normalized row matches all text filters."""
    return all(
        (
            _matches_values_filter(row.get("pipeline"), pipeline_filter),
            _matches_values_filter(row.get("run_type"), run_type_filter),
            _matches_values_filter(row.get("reason_code"), reason_code_filter),
            _matches_values_filter(row.get("field"), field_filter),
            _matches_values_filter(row.get("run_id"), run_id_filter),
            _matches_values_filter(row.get("payload_hash"), payload_hash_filter),
        )
    )


def _row_matches_time_bounds(
    row: JsonDict,
    *,
    from_bound: datetime | None,
    to_bound: datetime | None,
) -> bool:
    """Return True when ingestion timestamp is within optional bounds."""
    _, parsed_ts = _normalize_timestamp(row.get("ingestion_ts"))
    if from_bound is not None and (parsed_ts is None or parsed_ts < from_bound):
        return False
    return not (to_bound is not None and (parsed_ts is None or parsed_ts > to_bound))


def _iter_filtered_rows(
    table_records: list[JsonDict],
    *,
    run_type_lookup: dict[str, str] | None,
    pipeline: str | None,
    run_type: str | None,
    reason_code: str | None,
    field: str | None,
    run_id: str | None,
    payload_hash: str | None,
    from_ts: str | None,
    to_ts: str | None,
    include_payload: bool,
    include_payload_preview: bool,
) -> list[JsonDict]:
    """Apply server-side filtering for explorer rows."""
    pipeline_filter = _normalize_filter_values(pipeline)
    run_type_filter = _normalize_filter_values(run_type)
    reason_code_filter = _normalize_filter_values(reason_code)
    field_filter = _normalize_filter_values(field)
    run_id_filter = _normalize_filter_values(run_id)
    payload_hash_filter = _normalize_filter_values(payload_hash)
    from_bound = _parse_time_bound(from_ts)
    to_bound = _parse_time_bound(to_ts)

    rows: list[JsonDict] = []
    for record in table_records:
        row = _normalize_filtered_row(
            record,
            run_type_lookup=run_type_lookup,
            include_payload=include_payload,
            include_payload_preview=include_payload_preview,
        )
        if not _row_matches_filters(
            row,
            pipeline_filter=pipeline_filter,
            run_type_filter=run_type_filter,
            reason_code_filter=reason_code_filter,
            field_filter=field_filter,
            run_id_filter=run_id_filter,
            payload_hash_filter=payload_hash_filter,
        ):
            continue
        if not _row_matches_time_bounds(
            row,
            from_bound=from_bound,
            to_bound=to_bound,
        ):
            continue
        rows.append(row)
    return rows
