"""Quarantine service.

Business logic for quarantine management.
"""
import hashlib
import json
from collections.abc import Iterator
from datetime import datetime, UTC, timedelta
from typing import Any

from bioetl.domain.types import BatchID, ContentHash, DQStatus
from bioetl.infrastructure.quarantine.model import QuarantineRecord
from bioetl.infrastructure.quarantine.repository import QuarantineRepository


class QuarantineService:
    """Service for managing quarantined records."""

    MAX_PAYLOAD_SIZE = 64 * 1024  # 64 KB

    def __init__(self, repository: QuarantineRepository) -> None:
        self.repository = repository

    def write_record(
        self,
        pipeline: str,
        error_code: str,
        payload: dict[str, Any],
        bronze_batch_id: BatchID,
        bronze_file_uri: str | None = None,
        error_details: dict[str, Any] | None = None,
    ) -> ContentHash:
        """Write a record to quarantine."""
        payload_json = json.dumps(payload, ensure_ascii=True)
        truncated = False

        if len(payload_json) > self.MAX_PAYLOAD_SIZE:
            payload_json = payload_json[: self.MAX_PAYLOAD_SIZE]
            truncated = True

        payload_hash = hashlib.sha256(payload_json.encode("utf-8")).hexdigest()

        record = QuarantineRecord(
            ingestion_ts=datetime.now(UTC).isoformat(),
            pipeline=pipeline,
            error_code=error_code,
            payload=payload_json,
            payload_hash=payload_hash,
            payload_truncated=truncated,
            bronze_batch_id=str(bronze_batch_id),
            bronze_file_uri=bronze_file_uri or "",
            error_details=json.dumps(error_details or {}),
            dq_status=DQStatus.NEW.value
        )

        self.repository.save(record)
        return ContentHash(payload_hash)

    def inspect_records(
        self,
        pipeline: str,
        limit: int = 100,
        error_code: str | None = None,
        dq_status: DQStatus | None = None,
    ) -> list[dict[str, Any]]:
        """Inspect records with parsed JSON fields."""
        raw_records = self.repository.find_records(
            pipeline=pipeline,
            limit=limit,
            error_code=error_code,
            dq_status=dq_status,
            sort_descending=True
        )

        return [self._parse_record(r) for r in raw_records]

    def replay_records(
        self,
        pipeline: str,
        error_code: str | None = None,
        max_age_days: int = 7,
    ) -> Iterator[dict[str, Any]]:
        """Replay records for reprocessing."""
        raw_records = self.repository.find_records(
            pipeline=pipeline,
            limit=0, # No limit
            error_code=error_code,
            dq_status=DQStatus.NEW,
            max_age_days=max_age_days,
            sort_descending=False # Oldest first
        )

        for r in raw_records:
            yield self._parse_record(r)

    def purge_old_records(self, pipeline: str, older_than_days: int = 30) -> int:
        """Purge records older than N days."""
        cutoff_date = (datetime.now(UTC) - timedelta(days=older_than_days)).isoformat()
        return self.repository.delete_older_than(pipeline, cutoff_date)

    def update_record_status(self, payload_hash: str, new_status: DQStatus) -> bool:
        """Update status of a quarantined record."""
        return self.repository.update_status(payload_hash, new_status)

    def get_pipeline_stats(self, pipeline: str) -> dict[str, Any]:
        """Get statistics for a pipeline."""
        df = self.repository.get_dataframe(pipeline)

        if df is None or len(df) == 0:
            return {
                "total_records": 0,
                "by_error_code": {},
                "by_status": {},
                "oldest_record": None,
                "newest_record": None,
            }

        return {
            "total_records": len(df),
            "by_error_code": df["error_code"].value_counts().to_dict(),
            "by_status": df["dq_status"].value_counts().to_dict(),
            "oldest_record": df["ingestion_ts"].min(),
            "newest_record": df["ingestion_ts"].max(),
        }

    def _parse_record(self, record: dict[str, Any]) -> dict[str, Any]:
        """Parse JSON fields in a record dict."""
        record["payload"] = json.loads(record["payload"])
        record["error_details"] = json.loads(record["error_details"])
        return record
