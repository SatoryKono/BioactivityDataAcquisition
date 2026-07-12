"""Inspection operations for quarantine records."""

from __future__ import annotations

from typing import TYPE_CHECKING

from deltalake import DeltaTable
from deltalake.exceptions import TableNotFoundError

from bioetl.domain.serialization import deserialize_from_json
from bioetl.domain.types import JsonDict, QuarantineRecordStatus
from bioetl.infrastructure.quarantine.status_events import apply_latest_statuses

if TYPE_CHECKING:
    pass


def inspect_records(
    base_path: str,
    storage_options: dict[str, str] | None,
    pipeline: str,
    limit: int = 100,
    error_code: str | None = None,
    run_id: str | None = None,
    dq_status: QuarantineRecordStatus | None = None,
    *,
    status_events_path: str | None = None,
) -> list[JsonDict]:
    """Inspect quarantine records for a pipeline.

    Args:
        base_path: Base directory path.
        storage_options: Storage options.
        pipeline: Pipeline.
        limit: Maximum number of records to process.
        error_code: Error code.
        dq_status: DQ status.

    Returns:
        Result dictionary.
    """
    try:
        dt = DeltaTable(base_path, storage_options=storage_options)
    except TableNotFoundError:
        return []

    arrow_table = dt.to_pyarrow_table(partitions=[("pipeline", "=", pipeline)])
    status_filter = dq_status or QuarantineRecordStatus.NEW

    records = apply_latest_statuses(
        arrow_table.to_pylist(), status_events_path, storage_options
    )
    records = [
        record
        for record in records
        if str(record.get("pipeline", "")) == pipeline
        and (error_code is None or str(record.get("error_code", "")) == error_code)
        and (run_id is None or str(record.get("run_id", "")) == run_id)
        and str(record.get("dq_status", "")) == status_filter.value
    ]
    records.sort(key=lambda row: str(row.get("ingestion_ts", "")), reverse=True)
    if limit > 0:
        records = records[:limit]

    for record in records:
        record["payload"] = deserialize_from_json(record["payload"])
        record["metadata"] = deserialize_from_json(record.get("metadata", "{}"))
        record["error_details"] = deserialize_from_json(record["error_details"])

    return records
