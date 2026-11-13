"""Read APIs for quarantine explorer filtered views."""

from __future__ import annotations

import time
from datetime import datetime

import pyarrow as pa
import pyarrow.dataset as ds
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
    _parse_time_bound,
    _row_matches_time_bounds,
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


def _delta_partition_columns(dt: DeltaTable) -> frozenset[str]:
    """Return partition columns for historical Delta tables when available."""
    try:
        metadata = dt.metadata()
    except (AttributeError, RuntimeError, TypeError, ValueError):
        return frozenset()
    partition_columns = getattr(metadata, "partition_columns", ())
    if not isinstance(partition_columns, (list, tuple, set, frozenset)):
        return frozenset()
    return frozenset(str(column) for column in partition_columns)


def _load_scoped_pyarrow_table(
    dt: DeltaTable,
    *,
    pipeline_single: str,
    filters: list[tuple[str, str, object]] | None = None,
    columns: list[str] | None = None,
) -> pa.Table:
    """Read rows scoped by pipeline for partitioned and legacy non-partitioned tables."""
    if "pipeline" in _delta_partition_columns(dt):
        return dt.to_pyarrow_table(
            partitions=[("pipeline", "=", pipeline_single)],
            filters=filters or None,
            columns=columns,
        )
    return dt.to_pyarrow_table(
        partitions=None,
        filters=[*(filters or []), ("pipeline", "=", pipeline_single)],
        columns=columns,
    )


def _time_filter_expression(
    schema: pa.Schema,
    from_bound: datetime | None,
    to_bound: datetime | None,
) -> ds.Expression | None:
    """Push typed timestamps into Arrow; keep legacy text parsing compatible."""
    if from_bound is None and to_bound is None:
        return None
    if "ingestion_ts" not in schema.names:
        return ds.scalar(False)
    kind = schema.field("ingestion_ts").type
    if not pa.types.is_timestamp(kind):
        return None
    expression = ds.scalar(True)
    if from_bound is not None:
        expression = expression & (
            ds.field("ingestion_ts") >= pa.scalar(from_bound, type=kind)
        )
    if to_bound is not None:
        expression = expression & (
            ds.field("ingestion_ts") <= pa.scalar(to_bound, type=kind)
        )
    return expression


def _filter_legacy_time_batch(
    batch: pa.RecordBatch,
    from_bound: datetime | None,
    to_bound: datetime | None,
) -> pa.RecordBatch:
    """Filter only timestamp values before budgets, without decoding payload rows."""
    values = batch.column(batch.schema.get_field_index("ingestion_ts")).to_pylist()
    mask = [
        _row_matches_time_bounds(
            {"ingestion_ts": value}, from_bound=from_bound, to_bound=to_bound
        )
        for value in values
    ]
    return batch.filter(pa.array(mask, type=pa.bool_()))


def _load_bounded_scoped_pyarrow_table(
    dt: DeltaTable,
    *,
    pipeline_single: str,
    filters: list[tuple[str, str, object]] | None = None,
    columns: list[str] | None = None,
    from_ts: str | None = None,
    to_ts: str | None = None,
) -> pa.Table:
    """Read rows scoped by pipeline for partitioned and legacy non-partitioned tables."""
    partitioned = "pipeline" in _delta_partition_columns(dt)
    dataset = dt.to_pyarrow_dataset(
        partitions=[("pipeline", "=", pipeline_single)] if partitioned else None,
    )
    predicate = ds.field("pipeline") == pipeline_single
    for name, operator, value in filters or []:
        if operator != "=":
            raise ValueError("Unsupported quarantine filter operator")
        predicate = predicate & (ds.field(name) == value)
    from_bound = _parse_time_bound(from_ts)
    to_bound = _parse_time_bound(to_ts)
    time_filter = _time_filter_expression(dataset.schema, from_bound, to_bound)
    if time_filter is not None:
        predicate = predicate & time_filter
    legacy_time_filter = time_filter is None and (
        from_bound is not None or to_bound is not None
    )
    scan_columns = columns
    if legacy_time_filter and columns is not None and "ingestion_ts" not in columns:
        scan_columns = [*columns, "ingestion_ts"]
    scanner = dataset.scanner(
        columns=scan_columns,
        filter=predicate,
        batch_size=256,
        batch_readahead=1,
        fragment_readahead=1,
        use_threads=False,
    )
    result = _read_budgeted_batches(
        scanner,
        legacy_time_filter=legacy_time_filter,
        from_bound=from_bound,
        to_bound=to_bound,
    )
    return result.select(columns) if columns is not None else result


def _read_budgeted_batches(
    scanner: ds.Scanner,
    *,
    legacy_time_filter: bool,
    from_bound: datetime | None,
    to_bound: datetime | None,
) -> pa.Table:
    """Collect only selected batches under unchanged row, byte and time limits."""
    batches = []
    rows = size = 0
    deadline = time.monotonic() + 5.0
    for batch in scanner.to_batches():
        if legacy_time_filter:
            batch = _filter_legacy_time_batch(batch, from_bound, to_bound)
        rows += batch.num_rows
        size += batch.nbytes
        if rows > 10_000 or size > 8 * 1024 * 1024 or time.monotonic() > deadline:
            raise RuntimeError("Quarantine query budget exceeded; narrow the scope")
        if batch.num_rows:
            batches.append(batch)
    return pa.Table.from_batches(batches, schema=scanner.projected_schema)


def _filtered_projection_columns(
    dt: DeltaTable,
    *,
    include_payload: bool,
    include_payload_preview: bool,
) -> list[str] | None:
    """Return the smallest compatible Delta projection for explorer reads."""
    try:
        available = {str(field.name) for field in dt.schema().fields}
    except (AttributeError, RuntimeError, TypeError, ValueError):
        return None

    requested = [
        "ingestion_ts",
        "pipeline",
        "run_id",
        "run_type",
        "_run_type",
        "payload_hash",
        "error_code",
        "error_details",
        "dq_status",
    ]
    if include_payload or include_payload_preview:
        requested.append("payload")
    return [column for column in requested if column in available]


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

    arrow_table = _load_bounded_scoped_pyarrow_table(
        dt,
        pipeline_single=pipeline_single,
        filters=filters,
        from_ts=from_ts,
        to_ts=to_ts,
        columns=_filtered_projection_columns(
            dt,
            include_payload=include_payload,
            include_payload_preview=include_payload_preview,
        ),
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
    arrow_table = _load_bounded_scoped_pyarrow_table(
        dt,
        pipeline_single=pipeline_single,
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
