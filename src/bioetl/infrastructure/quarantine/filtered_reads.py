"""Helpers and read APIs for quarantine explorer filtered views."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from deltalake import DeltaTable
from deltalake.exceptions import TableNotFoundError

from bioetl.domain.serialization import deserialize_from_json
from bioetl.domain.types import JsonDict

__all__ = [
    "_build_reason_field_signature",
    "_build_reason_signature",
    "_increment_counter",
    "_load_filtered_rows",
    "_normalize_error_details",
    "_normalize_filter_values",
    "_single_filter_value",
    "get_filtered_filter_options",
    "get_filtered_record",
    "list_filtered_records",
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


def _parse_run_type_from_manifest_payload(payload: object) -> str | None:
    """Extract run_type from one run-manifest JSON payload."""
    if not isinstance(payload, dict):
        return None
    candidate = payload.get("run_type")
    if not isinstance(candidate, str):
        return None
    normalized = candidate.strip()
    return normalized or None


def _resolve_run_manifest_root(base_path: str) -> Path | None:
    """Resolve run-manifest root directory from quarantine base path."""
    quarantine_root = Path(base_path).resolve()
    candidate_roots = (
        quarantine_root.parent / "control" / "run_manifest",
        quarantine_root.parent / "control_plane" / "run_manifest",
    )
    for root in candidate_roots:
        if (root / "_by_run_id").exists():
            return root
    return None


def _resolve_manifest_id(run_index_root: Path, run_id: str) -> str | None:
    try:
        return (run_index_root / f"{run_id}.txt").read_text(
            encoding="utf-8"
        ).strip() or None
    except OSError:
        return None


def _resolve_manifest_run_type(manifest_root: Path, manifest_id: str) -> str | None:
    try:
        payload = json.loads(
            (manifest_root / f"{manifest_id}.json").read_text(encoding="utf-8")
        )
        return _parse_run_type_from_manifest_payload(payload)
    except (OSError, json.JSONDecodeError):
        return None


def _build_run_type_lookup(
    table_records: list[JsonDict],
    *,
    base_path: str,
) -> dict[str, str]:
    """Build run_id -> run_type mapping from control-plane run manifests."""
    manifest_root = _resolve_run_manifest_root(base_path)
    if manifest_root is None:
        return {}

    run_index_root = manifest_root / "_by_run_id"
    run_type_by_run_id: dict[str, str] = {}
    manifest_run_type_cache: dict[str, str | None] = {}

    for record in table_records:
        run_id_raw = record.get("run_id")
        if not isinstance(run_id_raw, str):
            continue
        run_id = run_id_raw.strip()
        if not run_id or run_id in run_type_by_run_id:
            continue

        manifest_id = _resolve_manifest_id(run_index_root, run_id)
        if not manifest_id:
            continue

        if manifest_id not in manifest_run_type_cache:
            manifest_run_type_cache[manifest_id] = _resolve_manifest_run_type(
                manifest_root, manifest_id
            )

        run_type = manifest_run_type_cache.get(manifest_id)
        if run_type:
            run_type_by_run_id[run_id] = run_type

    return run_type_by_run_id


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
        if not _matches_values_filter(row.get("pipeline"), pipeline_filter):
            continue
        if not _matches_values_filter(row.get("run_type"), run_type_filter):
            continue
        if not _matches_values_filter(row.get("reason_code"), reason_code_filter):
            continue
        if not _matches_values_filter(row.get("field"), field_filter):
            continue
        if not _matches_values_filter(row.get("run_id"), run_id_filter):
            continue
        if not _matches_values_filter(row.get("payload_hash"), payload_hash_filter):
            continue

        _, parsed_ts = _normalize_timestamp(row.get("ingestion_ts"))
        if from_bound is not None and (parsed_ts is None or parsed_ts < from_bound):
            continue
        if to_bound is not None and (parsed_ts is None or parsed_ts > to_bound):
            continue
        rows.append(row)
    return rows


def _load_filtered_rows(
    base_path: str,
    storage_options: dict[str, str] | None,
    *,
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
    """Read Silver-filter rows and apply scoped filtering in-memory."""
    pipeline_single = _single_filter_value(pipeline)
    if not pipeline_single:
        raise ValueError("Filtered quarantine reads require a scoped pipeline")

    try:
        dt = DeltaTable(base_path, storage_options=storage_options)
    except TableNotFoundError:
        return []

    filters: list[tuple[str, str, object]] = [
        ("error_code", "=", "FILTERED_OUT_SILVER"),
    ]
    run_id_single = _single_filter_value(run_id)
    if run_id_single:
        filters.append(("run_id", "=", run_id_single))
    payload_hash_single = _single_filter_value(payload_hash)
    if payload_hash_single:
        filters.append(("payload_hash", "=", payload_hash_single))

    partitions: list[tuple[str, str, object]] = [("pipeline", "=", pipeline_single)]

    arrow_table = dt.to_pyarrow_table(
        partitions=partitions,
        filters=filters,
    )
    table_records: list[JsonDict] = arrow_table.to_pylist()
    run_type_lookup = _build_run_type_lookup(table_records, base_path=base_path)
    return _iter_filtered_rows(
        table_records,
        run_type_lookup=run_type_lookup,
        pipeline=pipeline,
        run_type=run_type,
        reason_code=reason_code,
        field=field,
        run_id=run_id,
        payload_hash=payload_hash,
        from_ts=from_ts,
        to_ts=to_ts,
        include_payload=include_payload,
        include_payload_preview=include_payload_preview,
    )


def list_filtered_records(
    base_path: str,
    storage_options: dict[str, str] | None,
    *,
    pipeline: str | None = None,
    run_type: str | None = None,
    reason_code: str | None = None,
    field: str | None = None,
    run_id: str | None = None,
    payload_hash: str | None = None,
    from_ts: str | None = None,
    to_ts: str | None = None,
    limit: int = 50,
    offset: int = 0,
    sort: str = "ingestion_ts_desc",
) -> JsonDict:
    """Return paginated Silver-filter quarantine rows for explorer dashboards."""
    rows = _load_filtered_rows(
        base_path,
        storage_options,
        pipeline=pipeline,
        run_type=run_type,
        reason_code=reason_code,
        field=field,
        run_id=run_id,
        payload_hash=payload_hash,
        from_ts=from_ts,
        to_ts=to_ts,
        include_payload=False,
        include_payload_preview=False,
    )

    reverse = sort != "ingestion_ts_asc"
    rows.sort(
        key=lambda row: str(row.get("ingestion_ts", "")),
        reverse=reverse,
    )
    total = len(rows)
    clamped_limit = _clamp_limit(limit)
    clamped_offset = max(0, offset)
    paginated = rows[clamped_offset : clamped_offset + clamped_limit]
    return {
        "items": paginated,
        "total": total,
        "limit": clamped_limit,
        "offset": clamped_offset,
    }


def get_filtered_record(
    base_path: str,
    storage_options: dict[str, str] | None,
    *,
    payload_hash: str,
    pipeline: str | None = None,
) -> JsonDict | None:
    """Return detailed Silver-filter record by payload hash."""
    pipeline_single = _single_filter_value(pipeline)
    if not pipeline_single:
        raise ValueError("Filtered quarantine record lookup requires a scoped pipeline")

    try:
        dt = DeltaTable(base_path, storage_options=storage_options)
    except TableNotFoundError:
        return None

    filters: list[tuple[str, str, object]] = [
        ("error_code", "=", "FILTERED_OUT_SILVER"),
        ("payload_hash", "=", payload_hash),
    ]
    partitions: list[tuple[str, str, object]] = [("pipeline", "=", pipeline_single)]

    arrow_table = dt.to_pyarrow_table(
        partitions=partitions,
        filters=filters,
    )
    table_records: list[JsonDict] = arrow_table.to_pylist()
    if not table_records:
        return None
    run_type_lookup = _build_run_type_lookup(table_records, base_path=base_path)

    rows = _iter_filtered_rows(
        table_records,
        run_type_lookup=run_type_lookup,
        pipeline=pipeline,
        run_type=None,
        reason_code=None,
        field=None,
        run_id=None,
        payload_hash=payload_hash,
        from_ts=None,
        to_ts=None,
        include_payload=True,
        include_payload_preview=True,
    )
    if not rows:
        return None
    rows.sort(key=lambda row: str(row.get("ingestion_ts", "")), reverse=True)
    row = rows[0]
    row["cli_hint"] = (
        "bioetl quarantine resolve --pipeline "
        f"{row.get('pipeline', '')} --payload-hash {payload_hash} --status IGNORED"
    )
    return row


def get_filtered_filter_options(
    base_path: str,
    storage_options: dict[str, str] | None,
    *,
    pipeline: str | None = None,
    run_type: str | None = None,
    reason_code: str | None = None,
    field: str | None = None,
    run_id: str | None = None,
    from_ts: str | None = None,
    to_ts: str | None = None,
) -> JsonDict:
    """Return dynamic filter options for the quarantine explorer UI."""
    rows = _load_filtered_rows(
        base_path,
        storage_options,
        pipeline=pipeline,
        run_type=run_type,
        reason_code=reason_code,
        field=field,
        run_id=run_id,
        payload_hash=None,
        from_ts=from_ts,
        to_ts=to_ts,
        include_payload=False,
        include_payload_preview=False,
    )

    return {
        "pipelines": _collect_string_field_values(rows, "pipeline"),
        "run_types": _collect_string_field_values(rows, "run_type"),
        "reason_codes": _collect_string_field_values(rows, "reason_code"),
        "fields": _collect_string_field_values(rows, "field"),
        "run_ids": _collect_string_field_values(rows, "run_id"),
    }
