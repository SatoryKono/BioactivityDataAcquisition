"""In-memory quarantine implementation for testing.

Implements QuarantinePort interface without filesystem I/O.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime  # UTC used in add_record
from typing import Any

from bioetl.domain.ports.quality.quarantine import QuarantineWriteRequest
from bioetl.domain.types import BatchID, QuarantineRecordStatus, RunID


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
        *,
        ingestion_ts: datetime,
    ) -> None:
        """Write record to quarantine."""
        meta = metadata or {}

        record = {
            "ingestion_ts": ingestion_ts.isoformat(),
            "pipeline": pipeline,
            "error_code": error_code,
            "payload": payload,
            "bronze_batch_id": str(bronze_batch_id),
            "bronze_file_uri": meta.get("bronze_file_uri", ""),
            "error_details": meta.get("error_details", {}),
            "dq_status": QuarantineRecordStatus.NEW.value,
            "run_id": str(run_id) if run_id else "",
        }
        self._records[pipeline].append(record)

    async def write_many(self, records: list[QuarantineWriteRequest]) -> None:
        """Write multiple quarantine records."""
        for record in records:
            await self.write(
                pipeline=record["pipeline"],
                error_code=record["error_code"],
                payload=record["payload"],
                bronze_batch_id=record["bronze_batch_id"],
                run_id=record.get("run_id"),
                metadata=record.get("metadata"),
                ingestion_ts=record["ingestion_ts"],
            )

    async def inspect(
        self,
        pipeline: str,
        limit: int = 100,
        error_code: str | None = None,
        dq_status: QuarantineRecordStatus | None = None,
    ) -> list[dict[str, Any]]:
        """Inspect quarantine records."""
        records = self._records.get(pipeline, [])

        # Apply filters
        if error_code:
            records = [r for r in records if r["error_code"] == error_code]
        if dq_status:
            records = [r for r in records if r["dq_status"] == dq_status.value]

        return records[:limit]

    async def get_stats(
        self,
        pipeline: str,
        error_code: str | None = None,
    ) -> dict[str, Any]:
        """Get quarantine statistics for a pipeline."""
        records = self._records.get(pipeline, [])
        if error_code:
            records = [
                record for record in records if record["error_code"] == error_code
            ]

        # Count by error code
        by_error_code: dict[str, int] = defaultdict(int)
        by_status: dict[str, int] = defaultdict(int)
        for record in records:
            by_error_code[record["error_code"]] += 1
            by_status[record["dq_status"]] += 1

        return {
            "total": len(records),
            "total_count": len(records),
            "by_error_code": dict(by_error_code),
            "by_status": dict(by_status),
            "silver_filter_rejects": {
                "total_count": len(
                    [
                        record
                        for record in records
                        if record["error_code"] == "FILTERED_OUT_SILVER"
                    ]
                ),
                "by_reason_code": {},
                "by_field": {},
                "by_rule_type": {},
                "by_operator": {},
                "by_reason_code_field": {},
                "by_reason_signature": {},
            },
        }

    async def list_filtered_records(
        self,
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
    ) -> dict[str, Any]:
        """Return a minimal filtered-record list for tests."""
        del run_type, reason_code, field, from_ts, to_ts, sort
        if pipeline and pipeline.strip().lower() not in {"*", "all", "__all", ".*"}:
            pipelines = [item.strip() for item in pipeline.split(",") if item.strip()]
        else:
            pipelines = list(self._records.keys())
        records = []
        for pipeline_name in pipelines:
            records.extend(
                [
                    record
                    for record in self._records.get(pipeline_name, [])
                    if record.get("error_code") == "FILTERED_OUT_SILVER"
                ]
            )
        if run_id:
            records = [record for record in records if record.get("run_id") == run_id]
        if payload_hash:
            records = [
                record
                for record in records
                if record.get("payload_hash") == payload_hash
            ]
        total = len(records)
        return {
            "items": records[offset : offset + limit],
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    async def get_filtered_record(
        self,
        *,
        payload_hash: str,
        pipeline: str | None = None,
    ) -> dict[str, Any] | None:
        """Return one filtered record by payload hash."""
        pipelines = [pipeline] if pipeline else list(self._records.keys())
        for pipeline_name in pipelines:
            for record in self._records.get(pipeline_name, []):
                if (
                    record.get("error_code") == "FILTERED_OUT_SILVER"
                    and record.get("payload_hash") == payload_hash
                ):
                    return dict(record)
        return None

    async def get_filtered_stats(
        self,
        *,
        pipeline: str | None = None,
        run_type: str | None = None,
        reason_code: str | None = None,
        field: str | None = None,
        run_id: str | None = None,
        payload_hash: str | None = None,
        from_ts: str | None = None,
        to_ts: str | None = None,
    ) -> dict[str, Any]:
        """Return minimal aggregate stats for filtered records."""
        records = await self.list_filtered_records(
            pipeline=pipeline,
            run_type=run_type,
            reason_code=reason_code,
            field=field,
            run_id=run_id,
            payload_hash=payload_hash,
            from_ts=from_ts,
            to_ts=to_ts,
            limit=500,
            offset=0,
        )
        total = int(records.get("total", 0))
        return {
            "total": total,
            "by_reason_code": [],
            "by_field": [],
            "by_reason_signature": [],
            "bronze_records": 0,
            "reject_ratio": 0.0,
        }

    async def get_filtered_filter_options(
        self,
        *,
        pipeline: str | None = None,
        run_type: str | None = None,
        reason_code: str | None = None,
        field: str | None = None,
        run_id: str | None = None,
        from_ts: str | None = None,
        to_ts: str | None = None,
    ) -> dict[str, Any]:
        """Return empty filter options by default."""
        del run_type, reason_code, field, run_id, from_ts, to_ts
        if pipeline and pipeline.strip().lower() not in {"*", "all", "__all", ".*"}:
            pipelines = [item.strip() for item in pipeline.split(",") if item.strip()]
        else:
            pipelines = sorted(self._records.keys())
        return {
            "pipelines": pipelines,
            "run_types": [],
            "reason_codes": [],
            "fields": [],
            "run_ids": [],
        }

    async def aclose(self) -> None:
        """Close quarantine storage (no-op for in-memory)."""
        return None

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
            "dq_status": QuarantineRecordStatus.NEW.value,
            "run_id": "",
        }
        self._records[pipeline].append(record)
