"""Quarantine read operations: inspect, replay, statistics.

Contains operations for reading and analyzing quarantined records.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

import pyarrow.compute as pc
from deltalake import DeltaTable
from deltalake.exceptions import TableNotFoundError

from bioetl.domain.types import DQStatus
from bioetl.infrastructure.quarantine.helpers import quote_literal

if TYPE_CHECKING:
    from collections.abc import Iterator


def inspect_records(
    base_path: str,
    storage_options: dict[str, str] | None,
    pipeline: str,
    limit: int = 100,
    error_code: str | None = None,
    dq_status: DQStatus | None = None,
) -> list[dict[str, Any]]:
    """Inspect quarantine records for a pipeline."""
    try:
        dt = DeltaTable(base_path, storage_options=storage_options)
    except TableNotFoundError:
        return []

    arrow_table = dt.to_pyarrow_table(partitions=[("pipeline", "=", pipeline)])
    status_filter = dq_status or DQStatus.NEW

    mask = pc.equal(arrow_table["pipeline"], pipeline)
    if error_code:
        mask = pc.and_(mask, pc.equal(arrow_table["error_code"], error_code))
    mask = pc.and_(mask, pc.equal(arrow_table["dq_status"], status_filter.value))

    filtered_table = arrow_table.filter(mask)
    filtered_table = filtered_table.sort_by([("ingestion_ts", "descending")])

    if limit > 0:
        filtered_table = filtered_table.slice(length=limit)

    records = filtered_table.to_pylist()
    for record in records:
        record["payload"] = json.loads(record["payload"])
        record["error_details"] = json.loads(record["error_details"])

    return records  # type: ignore[no-any-return]


def replay_records(
    base_path: str,
    storage_options: dict[str, str] | None,
    pipeline: str,
    error_code: str | None = None,
    max_age_days: int = 7,
) -> Iterator[dict[str, Any]]:
    """Replay quarantine records for reprocessing."""
    try:
        dt = DeltaTable(base_path, storage_options=storage_options)
    except TableNotFoundError:
        return

    cutoff_date = datetime.now(UTC) - timedelta(days=max_age_days)
    arrow_table = dt.to_pyarrow_table(
        partitions=[("pipeline", "=", pipeline)],
        filters=[
            ("ingestion_ts", ">=", cutoff_date),
            ("dq_status", "=", DQStatus.NEW.value),
        ],
    )

    mask = pc.equal(arrow_table["pipeline"], pipeline)
    if error_code:
        mask = pc.and_(mask, pc.equal(arrow_table["error_code"], error_code))

    filtered_table = arrow_table.filter(mask)
    filtered_table = filtered_table.sort_by([("ingestion_ts", "ascending")])

    for record in filtered_table.to_pylist():
        record["payload"] = json.loads(record["payload"])
        record["error_details"] = json.loads(record["error_details"])
        yield record


def get_statistics(
    base_path: str,
    storage_options: dict[str, str] | None,
    pipeline: str,
) -> dict[str, Any]:
    """Get quarantine statistics for a pipeline."""
    empty_stats = {
        "total_records": 0,
        "by_error_code": {},
        "by_status": {},
        "oldest_record": None,
        "newest_record": None,
    }

    try:
        dt = DeltaTable(base_path, storage_options=storage_options)
    except TableNotFoundError:
        return empty_stats

    arrow_table = dt.to_pyarrow_table(partitions=[("pipeline", "=", pipeline)])
    if len(arrow_table) == 0:
        return empty_stats

    df = arrow_table.to_pylist()
    total_records = len(df)

    by_error_code: dict[str, int] = {}
    by_status: dict[str, int] = {}

    for record in df:
        error_code = record["error_code"]
        status = record["dq_status"]
        by_error_code[error_code] = by_error_code.get(error_code, 0) + 1
        by_status[status] = by_status.get(status, 0) + 1

    df_pandas = arrow_table.to_pandas()
    oldest_record = df_pandas["ingestion_ts"].min()
    newest_record = df_pandas["ingestion_ts"].max()

    return {
        "total_records": total_records,
        "by_error_code": by_error_code,
        "by_status": by_status,
        "oldest_record": oldest_record,
        "newest_record": newest_record,
    }


def purge_records(
    base_path: str,
    storage_options: dict[str, str] | None,
    pipeline: str,
    older_than_days: int = 30,
) -> int:
    """Purge old quarantine records, returns count of deleted records."""
    try:
        dt = DeltaTable(base_path, storage_options=storage_options)
    except TableNotFoundError:
        return 0

    cutoff_date = (datetime.now(UTC) - timedelta(days=older_than_days)).isoformat()

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
