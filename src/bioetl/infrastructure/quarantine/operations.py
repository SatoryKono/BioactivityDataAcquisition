"""Quarantine read operations: inspect, replay, statistics, and explorer endpoints.

Contains operations for reading and analyzing quarantined records.
"""

from __future__ import annotations

__all__ = [
    "get_filtered_filter_options",
    "get_filtered_record",
    "get_filtered_stats",
    "get_statistics",
    "inspect_records",
    "list_filtered_records",
    "purge_records",
    "replay_records",
]


from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

import pyarrow.compute as pc
from deltalake import DeltaTable
from deltalake.exceptions import TableNotFoundError

from bioetl.domain.serialization import deserialize_from_json
from bioetl.domain.types import JsonDict, QuarantineRecordStatus
from bioetl.infrastructure.quarantine.record_encoding import quote_literal

if TYPE_CHECKING:
    from collections.abc import Iterator


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
        record.get("run_type"),
    ):
        if isinstance(source, str) and source.strip():
            return source.strip()
    return ""


def _normalize_filtered_row(
    record: JsonDict,
    *,
    include_payload: bool,
) -> JsonDict:
    """Normalize one Silver-filter quarantine row for explorer responses."""
    payload_raw = record.get("payload")
    payload = (
        deserialize_from_json(payload_raw) if isinstance(payload_raw, str) else payload_raw
    )
    if not isinstance(payload, dict):
        payload = {"value": payload}
    error_details = _normalize_error_details(record)
    ingestion_ts_raw, _ = _normalize_timestamp(record.get("ingestion_ts"))

    reason_message = error_details.get("message")
    reason = (
        reason_message.strip()
        if isinstance(reason_message, str) and reason_message.strip()
        else record.get("error_code", "")
    )

    normalized: JsonDict = {
        "ingestion_ts": ingestion_ts_raw,
        "pipeline": record.get("pipeline", ""),
        "run_id": record.get("run_id", ""),
        "run_type": _extract_run_type(record, error_details),
        "payload_hash": record.get("payload_hash", ""),
        "reason_code": error_details.get("reason_code", ""),
        "rule_type": error_details.get("rule_type", ""),
        "field": error_details.get("field", ""),
        "operator": error_details.get("operator", ""),
        "expected": error_details.get("expected"),
        "actual": error_details.get("actual"),
        "dq_status": record.get("dq_status", ""),
        "reason": reason,
        "payload_preview": _build_payload_preview(payload),
    }
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
    if candidate.lower() in {"*", "all", "__all", ".*"}:
        return None
    values = {item.strip() for item in candidate.split(",") if item.strip()}
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
    pipeline: str | None,
    run_type: str | None,
    reason_code: str | None,
    field: str | None,
    run_id: str | None,
    payload_hash: str | None,
    from_ts: str | None,
    to_ts: str | None,
    include_payload: bool,
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
        row = _normalize_filtered_row(record, include_payload=include_payload)
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
        if from_bound is not None and (
            parsed_ts is None or parsed_ts < from_bound
        ):
            continue
        if to_bound is not None and (
            parsed_ts is None or parsed_ts > to_bound
        ):
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
) -> list[JsonDict]:
    """Read Silver-filter rows and apply scoped filtering in-memory."""
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

    partitions: list[tuple[str, str, object]] | None = None
    pipeline_single = _single_filter_value(pipeline)
    if pipeline_single:
        partitions = [("pipeline", "=", pipeline_single)]

    arrow_table = dt.to_pyarrow_table(
        partitions=partitions,
        filters=filters,
    )
    table_records: list[JsonDict] = arrow_table.to_pylist()
    return _iter_filtered_rows(
        table_records,
        pipeline=pipeline,
        run_type=run_type,
        reason_code=reason_code,
        field=field,
        run_id=run_id,
        payload_hash=payload_hash,
        from_ts=from_ts,
        to_ts=to_ts,
        include_payload=include_payload,
    )


def inspect_records(
    base_path: str,
    storage_options: dict[str, str] | None,
    pipeline: str,
    limit: int = 100,
    error_code: str | None = None,
    run_id: str | None = None,
    dq_status: QuarantineRecordStatus | None = None,
) -> list[JsonDict]:  # Any: quarantine record has heterogeneous values
    """Inspect quarantine records for a pipeline.

    Args:
        base_path: Base directory path.
        storage_options: Storage options.
        pipeline: Pipeline.
        limit: Maximum number of records to process.
        error_code: Error code.
        dq_status: Dq status.

    Returns:
        Result dictionary.
    """
    try:
        dt = DeltaTable(base_path, storage_options=storage_options)
    except TableNotFoundError:
        return []

    arrow_table = dt.to_pyarrow_table(partitions=[("pipeline", "=", pipeline)])
    status_filter = dq_status or QuarantineRecordStatus.NEW

    mask = pc.equal(arrow_table["pipeline"], pipeline)
    if error_code:
        mask = pc.and_(mask, pc.equal(arrow_table["error_code"], error_code))
    if run_id:
        mask = pc.and_(mask, pc.equal(arrow_table["run_id"], run_id))
    mask = pc.and_(mask, pc.equal(arrow_table["dq_status"], status_filter.value))

    filtered_table = arrow_table.filter(mask)
    filtered_table = filtered_table.sort_by([("ingestion_ts", "descending")])

    if limit > 0:
        filtered_table = filtered_table.slice(length=limit)

    records: list[JsonDict] = (  # Any: quarantine record has heterogeneous values
        filtered_table.to_pylist()
    )  # Any: quarantine record has heterogeneous values
    for record in records:
        record["payload"] = deserialize_from_json(record["payload"])
        record["error_details"] = deserialize_from_json(record["error_details"])

    return records


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
    try:
        dt = DeltaTable(base_path, storage_options=storage_options)
    except TableNotFoundError:
        return None

    filters: list[tuple[str, str, object]] = [
        ("error_code", "=", "FILTERED_OUT_SILVER"),
        ("payload_hash", "=", payload_hash),
    ]
    partitions: list[tuple[str, str, object]] | None = None
    if pipeline:
        partitions = [("pipeline", "=", pipeline)]

    arrow_table = dt.to_pyarrow_table(
        partitions=partitions,
        filters=filters,
    )
    table_records: list[JsonDict] = arrow_table.to_pylist()
    if not table_records:
        return None

    rows = _iter_filtered_rows(
        table_records,
        pipeline=pipeline,
        run_type=None,
        reason_code=None,
        field=None,
        run_id=None,
        payload_hash=payload_hash,
        from_ts=None,
        to_ts=None,
        include_payload=True,
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


def get_filtered_stats(
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
) -> JsonDict:
    """Return aggregate stats for filtered records under current scope."""
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
    )
    by_reason_code: dict[str, int] = {}
    by_field: dict[str, int] = {}
    by_reason_signature: dict[str, int] = {}
    for row in rows:
        _increment_counter(by_reason_code, row.get("reason_code"))
        _increment_counter(by_field, row.get("field"))
        signature = " | ".join(
            str(row.get(key, "")).strip()
            for key in ("reason_code", "rule_type", "field", "operator")
            if isinstance(row.get(key), str) and str(row.get(key)).strip()
        )
        if signature:
            by_reason_signature[signature] = by_reason_signature.get(signature, 0) + 1

    bronze_records = 0
    pipeline_filter = _normalize_filter_values(pipeline)
    if pipeline_filter is None:
        scoped_pipelines = {
            row.get("pipeline", "")
            for row in rows
            if isinstance(row.get("pipeline"), str) and row.get("pipeline", "").strip()
        }
    else:
        scoped_pipelines = set(pipeline_filter)
    run_id_single = _single_filter_value(run_id)
    for pipeline_name in sorted(scoped_pipelines):
        stats = get_statistics(
            base_path,
            storage_options,
            pipeline_name,
            error_code=None,
            run_id=run_id_single,
        )
        pipeline_total = stats.get("total_count")
        if isinstance(pipeline_total, int):
            bronze_records += pipeline_total

    total = len(rows)
    reject_ratio = float(total / bronze_records) if bronze_records > 0 else 0.0
    return {
        "total": total,
        "by_reason_code": [
            {"key": key, "count": value}
            for key, value in sorted(
                by_reason_code.items(),
                key=lambda item: item[1],
                reverse=True,
            )
        ],
        "by_field": [
            {"key": key, "count": value}
            for key, value in sorted(
                by_field.items(),
                key=lambda item: item[1],
                reverse=True,
            )
        ],
        "by_reason_signature": [
            {"key": key, "count": value}
            for key, value in sorted(
                by_reason_signature.items(),
                key=lambda item: item[1],
                reverse=True,
            )
        ],
        "bronze_records": bronze_records,
        "reject_ratio": reject_ratio,
    }


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
    )

    pipelines = sorted(
        {
            row.get("pipeline", "")
            for row in rows
            if isinstance(row.get("pipeline"), str) and row.get("pipeline")
        }
    )
    run_types = sorted(
        {
            row.get("run_type", "")
            for row in rows
            if isinstance(row.get("run_type"), str) and row.get("run_type")
        }
    )
    reason_codes = sorted(
        {
            row.get("reason_code", "")
            for row in rows
            if isinstance(row.get("reason_code"), str) and row.get("reason_code")
        }
    )
    fields = sorted(
        {
            row.get("field", "")
            for row in rows
            if isinstance(row.get("field"), str) and row.get("field")
        }
    )
    run_ids = sorted(
        {
            row.get("run_id", "")
            for row in rows
            if isinstance(row.get("run_id"), str) and row.get("run_id")
        }
    )

    return {
        "pipelines": pipelines,
        "run_types": run_types,
        "reason_codes": reason_codes,
        "fields": fields,
        "run_ids": run_ids,
    }


def replay_records(
    base_path: str,
    storage_options: dict[str, str] | None,
    pipeline: str,
    error_code: str | None = None,
    max_age_days: int = 7,
    *,
    now: datetime,
) -> Iterator[JsonDict]:  # Any: quarantine record has heterogeneous values
    """Replay quarantine records for reprocessing.

    Args:
        base_path: Path to the quarantine Delta table.
        storage_options: Storage options for Delta table access.
        pipeline: Pipeline name to filter by.
        error_code: Optional error code to filter by.
        max_age_days: Maximum age of records to replay (default 7).
        now: Current timestamp from application layer
             (single source of time per ADR-014). Required.

    Returns:
        Result dictionary.
    """
    try:
        dt = DeltaTable(base_path, storage_options=storage_options)
    except TableNotFoundError:
        return

    cutoff_date = now - timedelta(days=max_age_days)
    arrow_table = dt.to_pyarrow_table(
        partitions=[("pipeline", "=", pipeline)],
        filters=[
            ("ingestion_ts", ">=", cutoff_date),
            ("dq_status", "=", QuarantineRecordStatus.NEW.value),
        ],
    )

    mask = pc.equal(arrow_table["pipeline"], pipeline)
    if error_code:
        mask = pc.and_(mask, pc.equal(arrow_table["error_code"], error_code))

    filtered_table = arrow_table.filter(mask)
    filtered_table = filtered_table.sort_by([("ingestion_ts", "ascending")])

    for record in filtered_table.to_pylist():
        record["payload"] = deserialize_from_json(record["payload"])
        record["error_details"] = deserialize_from_json(record["error_details"])
        yield record


def get_statistics(
    base_path: str,
    storage_options: dict[str, str] | None,
    pipeline: str,
    error_code: str | None = None,
    run_id: str | None = None,
) -> JsonDict:  # Any: quarantine record has heterogeneous values
    """Get quarantine statistics for a pipeline.

    Args:
        base_path: Base directory path.
        storage_options: Storage options.
        pipeline: Pipeline.

    Returns:
        Statistics.
    """
    empty_stats = {
        "total_count": 0,
        "total_records": 0,
        "by_error_code": {},
        "by_status": {},
        "oldest_record": None,
        "newest_record": None,
        "silver_filter_rejects": {
            "total_count": 0,
            "by_reason_code": {},
            "by_field": {},
            "by_rule_type": {},
            "by_operator": {},
            "by_reason_code_field": {},
            "by_reason_signature": {},
        },
    }

    try:
        dt = DeltaTable(base_path, storage_options=storage_options)
    except TableNotFoundError:
        return empty_stats

    filters: list[tuple[str, str, object]] = []
    if error_code:
        filters.append(("error_code", "=", error_code))
    arrow_table = dt.to_pyarrow_table(
        partitions=[("pipeline", "=", pipeline)],
        filters=filters or None,
    )
    if len(arrow_table) == 0:
        return empty_stats
    if run_id:
        arrow_table = arrow_table.filter(pc.equal(arrow_table["run_id"], run_id))
        if len(arrow_table) == 0:
            return empty_stats

    df = arrow_table.to_pylist()
    total_records = len(df)

    by_error_code: dict[str, int] = {}
    by_status: dict[str, int] = {}
    by_reason_code: dict[str, int] = {}
    by_field: dict[str, int] = {}
    by_rule_type: dict[str, int] = {}
    by_operator: dict[str, int] = {}
    by_reason_code_field: dict[str, int] = {}
    by_reason_signature: dict[str, int] = {}
    silver_filter_total = 0

    for record in df:
        record_error_code = record["error_code"]
        status = record["dq_status"]
        by_error_code[record_error_code] = by_error_code.get(record_error_code, 0) + 1
        by_status[status] = by_status.get(status, 0) + 1
        if record_error_code != "FILTERED_OUT_SILVER":
            continue
        silver_filter_total += 1
        error_details = _normalize_error_details(record)
        _increment_counter(by_reason_code, error_details.get("reason_code"))
        _increment_counter(by_field, error_details.get("field"))
        _increment_counter(by_rule_type, error_details.get("rule_type"))
        _increment_counter(by_operator, error_details.get("operator"))
        reason_field_signature = _build_reason_field_signature(error_details)
        if reason_field_signature:
            by_reason_code_field[reason_field_signature] = (
                by_reason_code_field.get(reason_field_signature, 0) + 1
            )
        reason_signature = _build_reason_signature(error_details)
        if reason_signature:
            by_reason_signature[reason_signature] = (
                by_reason_signature.get(reason_signature, 0) + 1
            )

    df_pandas = arrow_table.to_pandas()
    oldest_record = df_pandas["ingestion_ts"].min()
    newest_record = df_pandas["ingestion_ts"].max()

    return {
        "total_count": total_records,
        "total_records": total_records,
        "by_error_code": by_error_code,
        "by_status": by_status,
        "oldest_record": oldest_record,
        "newest_record": newest_record,
        "silver_filter_rejects": {
            "total_count": silver_filter_total,
            "by_reason_code": by_reason_code,
            "by_field": by_field,
            "by_rule_type": by_rule_type,
            "by_operator": by_operator,
            "by_reason_code_field": by_reason_code_field,
            "by_reason_signature": by_reason_signature,
        },
    }


def purge_records(
    base_path: str,
    storage_options: dict[str, str] | None,
    pipeline: str,
    older_than_days: int = 30,
    *,
    now: datetime,
) -> int:
    """Purge old quarantine records, returns count of deleted records.

    Args:
        base_path: Path to the quarantine Delta table.
        storage_options: Storage options for Delta table access.
        pipeline: Pipeline name to filter by.
        older_than_days: Delete records older than this (default 30).
        now: Current timestamp from application layer
             (single source of time per ADR-014). Required.

    Returns:
        Count of deleted records.
    """
    try:
        dt = DeltaTable(base_path, storage_options=storage_options)
    except TableNotFoundError:
        return 0

    cutoff_date = (now - timedelta(days=older_than_days)).isoformat()

    predicate = (
        f"pipeline = {quote_literal(pipeline)} AND "
        f"ingestion_ts < {quote_literal(cutoff_date)}"
    )

    arrow_table = dt.to_pyarrow_table(
        partitions=[("pipeline", "=", pipeline)],
        filters=[("ingestion_ts", "<", cutoff_date)],
    )
    count_before = len(arrow_table)

    if count_before > 0:
        dt.delete(predicate)

    return count_before
