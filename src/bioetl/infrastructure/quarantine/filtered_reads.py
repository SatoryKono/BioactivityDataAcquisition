"""Read APIs for quarantine explorer filtered views."""

from __future__ import annotations

from deltalake import DeltaTable
from deltalake.exceptions import TableNotFoundError

from bioetl.domain.types import JsonDict
from bioetl.infrastructure.quarantine.filtered_manifest_support import (
    _build_run_type_lookup,
)
from bioetl.infrastructure.quarantine.filtered_read_support import (
    _build_reason_field_signature,
    _build_reason_signature,
    _clamp_limit,
    _collect_string_field_values,
    _increment_counter,
    _iter_filtered_rows,
    _normalize_error_details,
    _normalize_filter_values,
    _single_filter_value,
)

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
