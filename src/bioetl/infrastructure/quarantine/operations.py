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


from datetime import datetime, timedelta
from typing import TYPE_CHECKING

import pyarrow.compute as pc
from deltalake import DeltaTable
from deltalake.exceptions import TableNotFoundError

from bioetl.domain.serialization import deserialize_from_json
from bioetl.domain.types import JsonDict, QuarantineRecordStatus
from bioetl.infrastructure.quarantine.filtered_reads import (
    _increment_counter,
    _load_filtered_rows,
    _normalize_filter_values,
    _single_filter_value,
    get_filtered_filter_options,
    get_filtered_record,
    list_filtered_records,
)
from bioetl.infrastructure.quarantine.record_encoding import quote_literal
from bioetl.infrastructure.quarantine.statistics_support import (
    _build_reason_signature_from_row,
    _build_statistics_response,
    _count_bronze_records,
    _get_time_statistics,
    _process_quarantine_records,
    _sorted_counter_items,
)

if TYPE_CHECKING:
    from collections.abc import Iterator


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
        record["metadata"] = deserialize_from_json(record.get("metadata", "{}"))
        record["error_details"] = deserialize_from_json(record["error_details"])

    return records


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
        include_payload_preview=False,
    )
    by_reason_code: dict[str, int] = {}
    by_field: dict[str, int] = {}
    by_reason_signature: dict[str, int] = {}
    for row in rows:
        _increment_counter(by_reason_code, row.get("reason_code"))
        _increment_counter(by_field, row.get("field"))
        signature = _build_reason_signature_from_row(row)
        if signature:
            by_reason_signature[signature] = by_reason_signature.get(signature, 0) + 1

    pipeline_filter = _normalize_filter_values(pipeline)
    run_id_single = _single_filter_value(run_id)
    bronze_records = _count_bronze_records(
        rows,
        pipeline_filter=pipeline_filter,
        run_id_single=run_id_single,
        pipeline_stats_loader=lambda pipeline_name, scoped_run_id: get_statistics(
            base_path,
            storage_options,
            pipeline_name,
            error_code=None,
            run_id=scoped_run_id,
        ),
    )
    total = len(rows)
    reject_ratio = float(total / bronze_records) if bronze_records > 0 else 0.0
    return {
        "total": total,
        "by_reason_code": _sorted_counter_items(by_reason_code),
        "by_field": _sorted_counter_items(by_field),
        "by_reason_signature": _sorted_counter_items(by_reason_signature),
        "bronze_records": bronze_records,
        "reject_ratio": reject_ratio,
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
        record["metadata"] = deserialize_from_json(record.get("metadata", "{}"))
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

    (
        by_error_code,
        by_status,
        by_reason_code,
        by_field,
        by_rule_type,
        by_operator,
        by_reason_code_field,
        by_reason_signature,
        silver_filter_total,
    ) = _process_quarantine_records(df)

    oldest_record, newest_record = _get_time_statistics(arrow_table)

    return _build_statistics_response(
        total_records,
        by_error_code,
        by_status,
        oldest_record,
        newest_record,
        silver_filter_total,
        by_reason_code,
        by_field,
        by_rule_type,
        by_operator,
        by_reason_code_field,
        by_reason_signature,
    )


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
