"""In-memory quarantine implementation for testing.

Implements QuarantinePort interface without filesystem I/O.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime
from typing import Any

from bioetl.domain.types import BatchID, DQStatus, RunID


class InMemoryQuarantine:
    """In-memory quarantine storage for tests.

    Implements QuarantinePort interface from domain/ports.py.
    """

    def __init__(self) -> None:
        """Initialize in-memory quarantine storage."""
        # Keyed by pipeline name
        self._records: dict[str, list[dict[str, Any]]] = defaultdict(list)

    async def write(
        self,
        pipeline: str,
        error_code: str,
        payload: dict[str, Any],
        bronze_batch_id: BatchID,
        run_id: RunID | None = None,
        metadata: dict[str, Any] | None = None,
        ingestion_ts: datetime | None = None,
    ) -> None:
        """Write record to quarantine."""
        meta = metadata or {}
        effective_ts = ingestion_ts or datetime.now(UTC)

        record = {
            "ingestion_ts": effective_ts.isoformat(),
            "pipeline": pipeline,
            "error_code": error_code,
            "payload": payload,
            "bronze_batch_id": str(bronze_batch_id),
            "bronze_file_uri": meta.get("bronze_file_uri", ""),
            "error_details": meta.get("error_details", {}),
            "dq_status": DQStatus.NEW.value,
            "run_id": str(run_id) if run_id else "",
        }
        self._records[pipeline].append(record)

    async def inspect(
        self,
        pipeline: str,
        limit: int = 100,
        error_code: str | None = None,
        dq_status: DQStatus | None = None,
    ) -> list[dict[str, Any]]:
        """Inspect quarantine records."""
        records = self._records.get(pipeline, [])

        # Apply filters
        if error_code:
            records = [r for r in records if r["error_code"] == error_code]
        if dq_status:
            records = [r for r in records if r["dq_status"] == dq_status.value]

        return records[:limit]

    async def get_stats(self, pipeline: str) -> dict[str, Any]:
        """Get quarantine statistics for a pipeline."""
        records = self._records.get(pipeline, [])

        # Count by error code
        by_error_code: dict[str, int] = defaultdict(int)
        for record in records:
            by_error_code[record["error_code"]] += 1

        return {
            "total": len(records),
            "by_error_code": dict(by_error_code),
        }

    async def aclose(self) -> None:
        """Close quarantine storage (no-op for in-memory)."""
        pass

    def clear(self) -> None:
        """Clear all records (test utility)."""
        self._records.clear()

    def add_record(
        self,
        pipeline: str,
        error_code: str,
        payload: dict[str, Any],
    ) -> None:
        """Add a record directly (test utility).

        Convenience method for setting up test fixtures.
        """
        record = {
            "ingestion_ts": datetime.now(UTC).isoformat(),
            "pipeline": pipeline,
            "error_code": error_code,
            "payload": payload,
            "bronze_batch_id": "test-batch-id",
            "bronze_file_uri": "",
            "error_details": {},
            "dq_status": DQStatus.NEW.value,
            "run_id": "",
        }
        self._records[pipeline].append(record)
