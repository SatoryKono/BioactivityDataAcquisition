"""Lifecycle operations for quarantine records (replay, purge)."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from deltalake import DeltaTable
from deltalake.exceptions import TableNotFoundError

from bioetl.domain.serialization import deserialize_from_json
from bioetl.domain.types import JsonDict, QuarantineRecordStatus
from bioetl.infrastructure.quarantine.record_encoding import quote_literal
from bioetl.infrastructure.quarantine.status_events import apply_latest_statuses

if TYPE_CHECKING:
    from collections.abc import Iterator


def replay_records(
    base_path: str,
    storage_options: dict[str, str] | None,
    pipeline: str,
    error_code: str | None = None,
    max_age_days: int = 7,
    *,
    now: datetime,
    status_events_path: str | None = None,
) -> Iterator[JsonDict]:
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

    cutoff_date = (now - timedelta(days=max_age_days)).isoformat()
    arrow_table = dt.to_pyarrow_table(
        partitions=[("pipeline", "=", pipeline)],
        filters=[
            ("ingestion_ts", ">=", cutoff_date),
        ],
    )

    records = apply_latest_statuses(
        arrow_table.to_pylist(), status_events_path, storage_options
    )
    records = [
        record
        for record in records
        if str(record.get("pipeline", "")) == pipeline
        and str(record.get("dq_status", "")) == QuarantineRecordStatus.NEW.value
        and (error_code is None or str(record.get("error_code", "")) == error_code)
    ]
    records.sort(key=lambda row: str(row.get("ingestion_ts", "")))

    for record in records:
        record["payload"] = deserialize_from_json(record["payload"])
        record["metadata"] = deserialize_from_json(record.get("metadata", "{}"))
        record["error_details"] = deserialize_from_json(record["error_details"])
        yield record


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
