"""Unified quarantine table for all pipelines.

Implements RULES.md §2.6 - Quarantine Policy.

Requirements:
- REQ-QUARANTINE-001: Unified table common.quarantine
- REQ-QUARANTINE-002: Payload truncated to 64KB
- REQ-QUARANTINE-003: 30-day retention
- REQ-QUARANTINE-004: Link to Bronze via bronze_batch_id
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import TYPE_CHECKING, Any

import pyarrow as pa
from deltalake import DeltaTable, write_deltalake
from deltalake.exceptions import TableNotFoundError

from bioetl.domain.types import BatchID, DQStatus, RunID
from bioetl.infrastructure.quarantine.helpers import (
    MAX_PAYLOAD_SIZE,
    calculate_hash,
    quote_literal,
)
from bioetl.infrastructure.quarantine.operations import (
    get_statistics,
    inspect_records,
    purge_records,
    replay_records,
)

if TYPE_CHECKING:
    from collections.abc import Iterator


class UnifiedQuarantine:
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
        """Initialize unified quarantine for local filesystem."""
        self.base_path = base_path.rstrip("/")

    async def write(
        self,
        pipeline: str,
        error_code: str,
        payload: dict[str, Any],
        bronze_batch_id: BatchID,
        run_id: RunID | None = None,
        metadata: dict[str, Any] | None = None,
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
        payload_json = json.dumps(payload, ensure_ascii=True)

        if len(payload_json) > MAX_PAYLOAD_SIZE:
            payload_json = payload_json[:MAX_PAYLOAD_SIZE]
            truncated = True
        else:
            truncated = False

        payload_hash = calculate_hash(payload_json)
        meta = metadata or {}

        record = {
            "ingestion_ts": ingestion_ts.isoformat(),
            "pipeline": pipeline,
            "error_code": error_code,
            "payload": payload_json,
            "payload_hash": payload_hash,
            "payload_truncated": truncated,
            "bronze_batch_id": str(bronze_batch_id),
            "bronze_file_uri": meta.get("bronze_file_uri", ""),
            "error_details": json.dumps(meta.get("error_details", {})),
            "dq_status": DQStatus.NEW.value,
            "run_id": str(run_id) if run_id else "",
        }

        self._write_to_delta(record)

    def _write_to_delta(self, record: dict[str, Any]) -> None:
        """Write record to Delta table."""
        arrow_table = pa.Table.from_pylist([record])
        arrow_reader = pa.RecordBatchReader.from_batches(
            arrow_table.schema, arrow_table.to_batches()
        )

        try:
            write_deltalake(
                table_or_uri=self.base_path,
                data=arrow_reader,
                mode="append",
            )
        except TableNotFoundError:
            arrow_reader = pa.RecordBatchReader.from_batches(
                arrow_table.schema, arrow_table.to_batches()
            )
            write_deltalake(
                table_or_uri=self.base_path,
                data=arrow_reader,
                mode="append",
                partition_by=["pipeline"],
            )

    async def inspect(
        self,
        pipeline: str,
        limit: int = 100,
        error_code: str | None = None,
        dq_status: DQStatus | None = None,
    ) -> list[dict[str, Any]]:
        """Inspect quarantine records."""
        return inspect_records(
            self.base_path, None, pipeline, limit, error_code, dq_status
        )

    def replay(
        self,
        pipeline: str,
        error_code: str | None = None,
        max_age_days: int = 7,
    ) -> Iterator[dict[str, Any]]:
        """Replay quarantine records for reprocessing."""
        return replay_records(
            self.base_path, None, pipeline, error_code, max_age_days
        )

    def purge(self, pipeline: str, older_than_days: int = 30) -> int:
        """Purge old quarantine records."""
        return purge_records(
            self.base_path, None, pipeline, older_than_days
        )

    def update_status(self, payload_hash: str, new_status: DQStatus) -> bool:
        """Update DQ status for a quarantined record."""
        try:
            dt = DeltaTable(self.base_path)
        except TableNotFoundError:
            return False

        predicate = f"payload_hash = {quote_literal(payload_hash)}"
        arrow_table = dt.to_pyarrow_table(filters=[("payload_hash", "=", payload_hash)])

        if len(arrow_table) == 0:
            return False

        dt.update(
            updates={"dq_status": quote_literal(new_status.value)},
            predicate=predicate,
        )
        return True

    async def get_stats(self, pipeline: str) -> dict[str, Any]:
        """Get quarantine statistics for a pipeline."""
        return get_statistics(self.base_path, None, pipeline)

    async def aclose(self) -> None:
        """Close resources."""
        pass

    def _calculate_hash(self, payload_json: str) -> str:
        """Calculate SHA256 hash of payload for deduplication."""
        return calculate_hash(payload_json)
