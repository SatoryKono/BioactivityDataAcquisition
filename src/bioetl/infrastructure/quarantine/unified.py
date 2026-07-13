"""Unified quarantine table for all pipelines.

Implements RULES.md §2.6 - Quarantine Policy.

Requirements:
- REQ-QUARANTINE-001: Unified table common.quarantine
- REQ-QUARANTINE-002: Payload truncated to 64KB
- REQ-QUARANTINE-003: 30-day retention
- REQ-QUARANTINE-004: Link to Bronze via bronze_batch_id
"""

from __future__ import annotations

__all__ = ["UnifiedQuarantineAdapter"]


import asyncio
from datetime import datetime
from typing import TYPE_CHECKING

import pyarrow as pa
from deltalake import DeltaTable, write_deltalake
from deltalake.exceptions import TableNotFoundError

from bioetl.domain.ports import QuarantineWriteRequest
from bioetl.domain.serialization import serialize_to_json
from bioetl.domain.types import (
    BatchID,
    JsonDict,
    QuarantineRecordStatus,
    RunID,
)
from bioetl.infrastructure.quarantine._unified_filtered_mixin import (
    UnifiedQuarantineFilteredMixin,
)
from bioetl.infrastructure.quarantine.operations import (
    get_statistics,
    inspect_records,
    purge_records,
    replay_records,
)
from bioetl.infrastructure.quarantine.record_encoding import (
    MAX_PAYLOAD_SIZE,
    calculate_hash,
)
from bioetl.infrastructure.quarantine.status_events import (
    append_status_event,
    apply_latest_statuses,
)
from bioetl.infrastructure.quarantine.status_events import (
    status_events_path as build_status_events_path,
)

if TYPE_CHECKING:
    from collections.abc import Iterator


def _normalize_quarantine_record(record: QuarantineWriteRequest) -> JsonDict:
    """Normalize a write request into the stored quarantine schema."""
    payload = record["payload"]
    payload_json = serialize_to_json(payload, ensure_ascii=True)

    if len(payload_json) > MAX_PAYLOAD_SIZE:
        payload_json = payload_json[:MAX_PAYLOAD_SIZE]
        truncated = True
    else:
        truncated = False

    payload_hash = calculate_hash(payload_json)
    meta = record.get("metadata") or {}
    bronze_batch_id = record["bronze_batch_id"]
    run_id = record.get("run_id")
    ingestion_ts = record["ingestion_ts"]

    return {
        "ingestion_ts": ingestion_ts.isoformat(),
        "pipeline": record["pipeline"],
        "error_code": record["error_code"],
        "payload": payload_json,
        "metadata": serialize_to_json(meta),
        "payload_hash": payload_hash,
        "payload_truncated": truncated,
        "bronze_batch_id": str(bronze_batch_id),
        "bronze_file_uri": meta.get("bronze_file_uri", ""),
        "error_details": serialize_to_json(meta.get("error_details", {})),
        "dq_status": QuarantineRecordStatus.NEW.value,
        "run_id": str(run_id) if run_id else "",
    }


def _write_records_to_delta(base_path: str, records: list[JsonDict]) -> None:
    """Write normalized records to Delta table."""
    arrow_table = pa.Table.from_pylist(records)
    arrow_reader = pa.RecordBatchReader.from_batches(
        arrow_table.schema, arrow_table.to_batches()
    )

    try:
        write_deltalake(
            table_or_uri=base_path,
            data=arrow_reader,
            mode="append",
        )
    except TableNotFoundError:
        arrow_reader = pa.RecordBatchReader.from_batches(
            arrow_table.schema, arrow_table.to_batches()
        )
        write_deltalake(
            table_or_uri=base_path,
            data=arrow_reader,
            mode="append",
            partition_by=["pipeline"],
        )


class UnifiedQuarantineAdapter(UnifiedQuarantineFilteredMixin):
    """Unified quarantine table for failed records.

    All pipelines write to the same `common.quarantine` table.
    Implements QuarantinePort interface from domain/ports.py.
    Local filesystem storage only.
    """

    # Maximum payload size (64KB)
    MAX_PAYLOAD_SIZE = MAX_PAYLOAD_SIZE

    def __init__(
        self,
        base_path: str,
    ) -> None:
        """Initialize unified quarantine for local filesystem.

        Args:
            base_path: Root directory path for the quarantine Delta table.
                Trailing slashes are stripped automatically.

        """
        self.base_path = base_path.rstrip("/")
        self.status_events_path = build_status_events_path(self.base_path)

    async def write(
        self,
        pipeline: str,
        error_code: str,
        payload: JsonDict,  # Any: quarantine payload has heterogeneous values
        bronze_batch_id: BatchID,
        run_id: RunID | None = None,
        entry_id: str | None = None,
        metadata: JsonDict  # Any: metadata values are heterogeneous
        | None = None,
        *,
        ingestion_ts: datetime,
    ) -> None:
        """Write record to quarantine.

        Args:
            pipeline: The name of the pipeline where the error occurred.
            error_code: A code identifying the type of error.
            payload: The record that failed processing.
            bronze_batch_id: The ID of the bronze batch containing the record.
            run_id: Optional ID of the pipeline run for traceability.
            metadata: Optional additional metadata (e.g., error_details, bronze_file_uri).
            ingestion_ts: Ingestion timestamp from application layer
                         (single source of time per ADR-014). Required.

        """
        await self.write_many(
            [
                {
                    "pipeline": pipeline,
                    "error_code": error_code,
                    "payload": payload,
                    "bronze_batch_id": bronze_batch_id,
                    "run_id": run_id,
                    "entry_id": entry_id,
                    "metadata": metadata,
                    "ingestion_ts": ingestion_ts,
                }
            ]
        )

    async def write_many(
        self,
        records: list[QuarantineWriteRequest],
    ) -> None:
        """Write multiple quarantine records in one Delta append."""
        if not records:
            return
        normalized_records = [self._normalize_record(record) for record in records]
        self._write_to_delta(normalized_records)

    def _normalize_record(
        self,
        record: QuarantineWriteRequest,
    ) -> JsonDict:
        """Normalize a write request into the stored quarantine schema."""
        return _normalize_quarantine_record(record)

    def _write_to_delta(
        self,
        records: list[JsonDict],  # Any: quarantine record has heterogeneous values
    ) -> None:
        """Write normalized records to Delta table."""
        _write_records_to_delta(self.base_path, records)

    async def inspect(
        self,
        pipeline: str,
        limit: int = 100,
        error_code: str | None = None,
        run_id: str | None = None,
        dq_status: QuarantineRecordStatus | None = None,
    ) -> list[JsonDict]:  # Any: quarantine record has heterogeneous values
        """Inspect quarantine records matching the given filters.

        Args:
            pipeline: Pipeline name to filter by.
            limit: Maximum number of records to return.
            error_code: Optional error code to filter by.
            run_id: Optional run ID to filter by.
            dq_status: Optional quarantine status to filter by.

        Returns:
            List of quarantine record dicts with payload, error, and status fields.
        """
        return inspect_records(
            self.base_path,
            None,
            pipeline,
            limit,
            error_code,
            run_id,
            dq_status,
            status_events_path=self.status_events_path,
        )

    def replay(
        self,
        pipeline: str,
        error_code: str | None = None,
        max_age_days: int = 7,
        *,
        now: datetime,
    ) -> Iterator[JsonDict]:  # Any: quarantine record has heterogeneous values
        """Replay quarantine records for reprocessing.

        Args:
            pipeline: Pipeline name to filter by.
            error_code: Optional error code to filter by.
            max_age_days: Maximum age of records to replay (default 7).
            now: Current timestamp from application layer
                 (single source of time per ADR-014). Required.

        Returns:
            Iterator yielding individual quarantine record dicts for reprocessing.
        """
        return replay_records(
            self.base_path,
            None,
            pipeline,
            error_code,
            max_age_days,
            now=now,
            status_events_path=self.status_events_path,
        )

    def purge(
        self,
        pipeline: str,
        older_than_days: int = 30,
        *,
        now: datetime,
    ) -> int:
        """Purge old quarantine records.

        Args:
            pipeline: Pipeline name to filter by.
            older_than_days: Delete records older than this (default 30).
            now: Current timestamp from application layer
                 (single source of time per ADR-014). Required.

        Returns:
            Count of deleted records.
        """
        return purge_records(self.base_path, None, pipeline, older_than_days, now=now)

    def update_status(
        self, payload_hash: str, new_status: QuarantineRecordStatus
    ) -> bool:
        """Update DQ status for a quarantined record.

        Args:
            payload_hash: SHA-256 hash identifying the quarantined record.
            new_status: New quarantine status to set.

        Returns:
            True if a matching record was found and status was appended, False if no
            quarantine table exists or no record matches the hash.
        """
        try:
            dt = DeltaTable(self.base_path)
        except TableNotFoundError:
            return False

        arrow_table = dt.to_pyarrow_table(filters=[("payload_hash", "=", payload_hash)])

        if len(arrow_table) == 0:
            return False

        append_status_event(
            self.status_events_path,
            None,
            payload_hash=payload_hash,
            new_status=new_status,
        )
        return True

    def get_record(
        self,
        *,
        payload_hash: str,
        pipeline: str | None = None,
    ) -> JsonDict | None:
        """Return one quarantine record including payload and metadata."""
        try:
            dt = DeltaTable(self.base_path)
        except TableNotFoundError:
            return None

        filters: list[tuple[str, str, object]] = [("payload_hash", "=", payload_hash)]
        if pipeline:
            filters.append(("pipeline", "=", pipeline))

        try:
            arrow_table = dt.to_pyarrow_table(
                filters=filters,
            )
            records: list[JsonDict] = arrow_table.to_pylist()
        except pa.ArrowNotImplementedError:
            # Delta updates can materialize string_view columns that pyarrow cannot
            # filter directly on some local versions. Fall back to a read-only scan
            # and keep payload filtering in process so status updates remain inspectable.
            records = [
                row
                for row in dt.to_pyarrow_table().to_pylist()
                if str(row.get("payload_hash", "")) == payload_hash
                and (pipeline is None or str(row.get("pipeline", "")) == pipeline)
            ]
        if not records:
            return None
        records.sort(key=lambda row: str(row.get("ingestion_ts", "")), reverse=True)
        records = apply_latest_statuses(records, self.status_events_path, None)
        return records[0]

    async def get_stats(
        self,
        pipeline: str,
        error_code: str | None = None,
        run_id: str | None = None,
    ) -> JsonDict:  # Any: quarantine record has heterogeneous values
        """Get quarantine statistics for a pipeline.

        Args:
            pipeline: Pipeline name to compute statistics for.
            error_code: Optional error code to scope the statistics.
            run_id: Optional run ID to scope the statistics.

        Returns:
            Dict with counts by error code, status distribution, and totals.
        """
        await asyncio.sleep(0)
        return get_statistics(
            self.base_path,
            None,
            pipeline,
            error_code,
            run_id,
            status_events_path=self.status_events_path,
        )

    async def aclose(self) -> None:
        """Close resources."""
        await asyncio.sleep(0)
