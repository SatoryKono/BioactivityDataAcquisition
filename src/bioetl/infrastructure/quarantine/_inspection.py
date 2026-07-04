"""Inspection operations for quarantine records."""

from __future__ import annotations

from typing import TYPE_CHECKING

from deltalake import DeltaTable
from deltalake.exceptions import TableNotFoundError

from bioetl.domain.serialization import deserialize_from_json
from bioetl.domain.types import JsonDict, QuarantineRecordStatus
from bioetl.infrastructure.quarantine._pyarrow_helpers import (
    and_mask,
    equal_mask,
)

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

    mask = equal_mask(arrow_table["pipeline"], pipeline)
    if error_code:
        mask = and_mask(mask, equal_mask(arrow_table["error_code"], error_code))
    if run_id:
        mask = and_mask(mask, equal_mask(arrow_table["run_id"], run_id))
    mask = and_mask(mask, equal_mask(arrow_table["dq_status"], status_filter.value))

    filtered_table = arrow_table.filter(mask)
    filtered_table = filtered_table.sort_by([("ingestion_ts", "descending")])

    if limit > 0:
        filtered_table = filtered_table.slice(length=limit)

    records: list[JsonDict] = filtered_table.to_pylist()
    for record in records:
        record["payload"] = deserialize_from_json(record["payload"])
        record["metadata"] = deserialize_from_json(record.get("metadata", "{}"))
        record["error_details"] = deserialize_from_json(record["error_details"])

    return records
