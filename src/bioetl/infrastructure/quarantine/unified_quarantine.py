"""Unified quarantine table for all pipelines.

Implements RULES.md §2.6 - Quarantine Policy.

Requirements:
- REQ-QUARANTINE-001: Unified table common.quarantine
- REQ-QUARANTINE-002: Payload truncated to 64KB
- REQ-QUARANTINE-003: 30-day retention
- REQ-QUARANTINE-004: Link to Bronze via bronze_batch_id

Architecture:
- Single Delta Lake table for all pipelines
- Schema: ingestion_ts, pipeline, error_code, payload, payload_hash,
          bronze_batch_id, bronze_file_uri, dq_status
- Operations: write, inspect, replay, purge
- Deduplication via payload_hash
"""

import hashlib
import json
from collections.abc import Iterator
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from deltalake import DeltaTable, write_deltalake
from deltalake.exceptions import TableNotFoundError

from bioetl.domain.types import BatchID, ContentHash, DQStatus


class UnifiedQuarantine:
    """Unified quarantine table for failed records.

    All pipelines write to the same `common.quarantine` table.
    Implements QuarantinePort interface from domain/ports.py.

    Example:
        >>> quarantine = UnifiedQuarantine(
        ...     base_path="s3://bioetl-silver/common/quarantine",
        ...     storage_options={"AWS_ENDPOINT_URL": "http://localhost:9000"}
        ... )
        >>> from uuid import uuid4
        >>> batch_id = BatchID(uuid4())
        >>> hash_val = quarantine.write(
        ...     pipeline="chembl_activity",
        ...     error_code="SCHEMA_VIOLATION",
        ...     payload={"id": "invalid", "value": "not_a_number"},
        ...     bronze_batch_id=batch_id,
        ...     bronze_file_uri="s3://bronze/v1/chembl/activity/2025-12-15/batch_xxx.jsonl.zst",
        ...     error_details={"field": "value", "reason": "Expected float, got string"}
        ... )
        >>> print(f"Quarantined with hash: {hash_val}")
    """

    # Maximum payload size (64KB)
    MAX_PAYLOAD_SIZE = 64 * 1024  # 64 KB

    def __init__(
        self,
        base_path: str,
        storage_options: dict[str, str] | None = None,
    ) -> None:
        """Initialize unified quarantine.

        Args:
            base_path: Path to quarantine table (e.g., 's3://bioetl-silver/common/quarantine')
            storage_options: Storage configuration for S3/MinIO
        """
        self.base_path = base_path.rstrip("/")
        self.storage_options = storage_options or {}

    def write(
        self,
        pipeline: str,
        error_code: str,
        payload: dict[str, Any],
        bronze_batch_id: BatchID,
        bronze_file_uri: str | None = None,
        error_details: dict[str, Any] | None = None,
    ) -> ContentHash:
        """Write record to quarantine.

        Requirements:
        - REQ-QUARANTINE-001: Unified table common.quarantine
        - REQ-QUARANTINE-002: Payload truncated to 64KB
        - REQ-QUARANTINE-004: Link to Bronze

        Args:
            pipeline: Pipeline name (e.g., 'chembl_activity')
            error_code: Error type (e.g., 'SCHEMA_VIOLATION', 'INVALID_DATA')
            payload: Raw record (will be truncated to 64KB)
            bronze_batch_id: Reference to Bronze batch
            bronze_file_uri: Full S3 path to Bronze file (optional)
            error_details: Additional error context (e.g., validation errors)

        Returns:
            Content hash (SHA256) for deduplication

        Example:
            >>> quarantine = UnifiedQuarantine(base_path="s3://bioetl-silver/common/quarantine")
            >>> hash_val = quarantine.write(
            ...     pipeline="chembl_activity",
            ...     error_code="MISSING_REQUIRED_FIELD",
            ...     payload={"value": 5.5},  # Missing 'id' field
            ...     bronze_batch_id=BatchID(UUID("...")),
            ...     error_details={"field": "id", "reason": "Required field missing"}
            ... )
        """
        # Serialize payload to JSON
        payload_json = json.dumps(payload, ensure_ascii=True)

        # Truncate if too large (REQ-QUARANTINE-002)
        if len(payload_json) > self.MAX_PAYLOAD_SIZE:
            payload_json = payload_json[: self.MAX_PAYLOAD_SIZE]
            truncated = True
        else:
            truncated = False

        # Calculate payload hash for deduplication
        payload_hash = self._calculate_hash(payload_json)

        # Prepare quarantine record
        record = {
            "ingestion_ts": datetime.utcnow().isoformat(),
            "pipeline": pipeline,
            "error_code": error_code,
            "payload": payload_json,
            "payload_hash": payload_hash,
            "payload_truncated": truncated,
            "bronze_batch_id": str(bronze_batch_id),
            "bronze_file_uri": bronze_file_uri or "",
            "error_details": json.dumps(error_details or {}),
            "dq_status": DQStatus.NEW.value,
        }

        # Write to Delta table
        try:
            # Try to append to existing table
            write_deltalake(
                table_or_uri=self.base_path,
                data=[record],
                mode="append",
                storage_options=self.storage_options,
            )
        except TableNotFoundError:
            # Table doesn't exist, create it with schema
            write_deltalake(
                table_or_uri=self.base_path,
                data=[record],
                mode="append",
                partition_by=["pipeline"],  # Partition by pipeline for efficient queries
                storage_options=self.storage_options,
            )

        return ContentHash(payload_hash)

    def inspect(
        self,
        pipeline: str,
        limit: int = 100,
        error_code: str | None = None,
        dq_status: DQStatus | None = None,
    ) -> list[dict[str, Any]]:
        """Inspect quarantine records.

        Args:
            pipeline: Pipeline name
            limit: Maximum records to return (default: 100)
            error_code: Filter by error code (optional)
            dq_status: Filter by DQ status (optional, default: NEW)

        Returns:
            List of quarantine records

        Example:
            >>> quarantine = UnifiedQuarantine(base_path="s3://bioetl-silver/common/quarantine")
            >>> records = quarantine.inspect("chembl_activity", limit=10)
            >>> for rec in records:
            ...     print(f"{rec['error_code']}: {rec['payload'][:100]}")
        """
        try:
            dt = DeltaTable(self.base_path, storage_options=self.storage_options)
        except TableNotFoundError:
            # Table doesn't exist yet
            return []

        # Convert to PyArrow table
        arrow_table = dt.to_pyarrow_table()

        # Apply filters
        import pyarrow.compute as pc

        # Filter by pipeline
        mask = pc.equal(arrow_table["pipeline"], pipeline)

        # Filter by error_code if specified
        if error_code:
            mask = pc.and_(mask, pc.equal(arrow_table["error_code"], error_code))

        # Filter by dq_status if specified (default: NEW)
        status_filter = dq_status or DQStatus.NEW
        mask = pc.and_(mask, pc.equal(arrow_table["dq_status"], status_filter.value))

        # Apply filter
        filtered_table = arrow_table.filter(mask)

        # Sort by ingestion_ts descending (most recent first)
        filtered_table = filtered_table.sort_by([("ingestion_ts", "descending")])

        # Limit results
        if limit > 0:
            filtered_table = filtered_table.slice(length=limit)

        # Convert to list of dicts
        records = filtered_table.to_pylist()

        # Parse JSON fields
        for record in records:
            record["payload"] = json.loads(record["payload"])
            record["error_details"] = json.loads(record["error_details"])

        return records

    def replay(
        self,
        pipeline: str,
        error_code: str | None = None,
        max_age_days: int = 7,
    ) -> Iterator[dict[str, Any]]:
        """Replay quarantine records for reprocessing.

        Args:
            pipeline: Pipeline name
            error_code: Filter by error code (optional)
            max_age_days: Only replay records newer than this (default: 7 days)

        Yields:
            Quarantine records ready for reprocessing

        Example:
            >>> quarantine = UnifiedQuarantine(base_path="s3://bioetl-silver/common/quarantine")
            >>> for record in quarantine.replay("chembl_activity", max_age_days=3):
            ...     # Reprocess record
            ...     print(f"Reprocessing: {record['payload']}")
        """
        try:
            dt = DeltaTable(self.base_path, storage_options=self.storage_options)
        except TableNotFoundError:
            # Table doesn't exist yet
            return

        # Convert to PyArrow table
        arrow_table = dt.to_pyarrow_table()

        # Apply filters
        import pyarrow.compute as pc

        # Filter by pipeline
        mask = pc.equal(arrow_table["pipeline"], pipeline)

        # Filter by error_code if specified
        if error_code:
            mask = pc.and_(mask, pc.equal(arrow_table["error_code"], error_code))

        # Filter by max_age_days
        cutoff_date = (datetime.utcnow() - timedelta(days=max_age_days)).isoformat()
        mask = pc.and_(
            mask,
            pc.greater_equal(arrow_table["ingestion_ts"], cutoff_date),
        )

        # Filter by dq_status (only NEW records)
        mask = pc.and_(mask, pc.equal(arrow_table["dq_status"], DQStatus.NEW.value))

        # Apply filter
        filtered_table = arrow_table.filter(mask)

        # Sort by ingestion_ts ascending (oldest first)
        filtered_table = filtered_table.sort_by([("ingestion_ts", "ascending")])

        # Convert to list and yield
        records = filtered_table.to_pylist()
        for record in records:
            # Parse JSON fields
            record["payload"] = json.loads(record["payload"])
            record["error_details"] = json.loads(record["error_details"])
            yield record

    def purge(self, pipeline: str, older_than_days: int = 30) -> int:
        """Purge old quarantine records.

        Requirements:
        - REQ-QUARANTINE-003: 30-day retention

        Args:
            pipeline: Pipeline name
            older_than_days: Delete records older than this (default: 30 days)

        Returns:
            Number of deleted records

        Example:
            >>> quarantine = UnifiedQuarantine(base_path="s3://bioetl-silver/common/quarantine")
            >>> deleted = quarantine.purge("chembl_activity", older_than_days=30)
            >>> print(f"Deleted {deleted} old records")
        """
        try:
            dt = DeltaTable(self.base_path, storage_options=self.storage_options)
        except TableNotFoundError:
            # Table doesn't exist yet
            return 0

        # Calculate cutoff date
        cutoff_date = (datetime.utcnow() - timedelta(days=older_than_days)).isoformat()

        # Delete old records using Delta Lake delete
        # Build predicate: pipeline = 'X' AND ingestion_ts < 'YYYY-MM-DD'
        predicate = f"pipeline = '{pipeline}' AND ingestion_ts < '{cutoff_date}'"

        # Get count before deletion
        arrow_table = dt.to_pyarrow_table()
        import pyarrow.compute as pc

        mask = pc.and_(
            pc.equal(arrow_table["pipeline"], pipeline),
            pc.less(arrow_table["ingestion_ts"], cutoff_date),
        )
        count_before = pc.sum(pc.cast(mask, "int64")).as_py()

        # Execute delete
        dt.delete(predicate)

        return count_before

    def update_status(
        self,
        payload_hash: str,
        new_status: DQStatus,
    ) -> bool:
        """Update DQ status for a quarantined record.

        Args:
            payload_hash: Payload hash to identify record
            new_status: New DQ status (IGNORED or REPROCESSED)

        Returns:
            True if updated, False if not found

        Example:
            >>> quarantine = UnifiedQuarantine(base_path="s3://bioetl-silver/common/quarantine")
            >>> quarantine.update_status("abc123...", DQStatus.IGNORED)
        """
        try:
            dt = DeltaTable(self.base_path, storage_options=self.storage_options)
        except TableNotFoundError:
            return False

        # Update using Delta Lake update
        # Build predicate: payload_hash = 'X'
        predicate = f"payload_hash = '{payload_hash}'"

        # Check if record exists
        arrow_table = dt.to_pyarrow_table()
        import pyarrow.compute as pc

        mask = pc.equal(arrow_table["payload_hash"], payload_hash)
        count = pc.sum(pc.cast(mask, "int64")).as_py()

        if count == 0:
            return False

        # Execute update
        dt.update(
            updates={"dq_status": f"'{new_status.value}'"},
            predicate=predicate,
        )

        return True

    def get_stats(self, pipeline: str) -> dict[str, Any]:
        """Get quarantine statistics for a pipeline.

        Args:
            pipeline: Pipeline name

        Returns:
            Dictionary with statistics:
            - total_records: Total quarantined records
            - by_error_code: Count by error code
            - by_status: Count by DQ status
            - oldest_record: Timestamp of oldest record
            - newest_record: Timestamp of newest record

        Example:
            >>> quarantine = UnifiedQuarantine(base_path="s3://bioetl-silver/common/quarantine")
            >>> stats = quarantine.get_stats("chembl_activity")
            >>> print(f"Total: {stats['total_records']}")
            >>> print(f"By error: {stats['by_error_code']}")
        """
        try:
            dt = DeltaTable(self.base_path, storage_options=self.storage_options)
        except TableNotFoundError:
            return {
                "total_records": 0,
                "by_error_code": {},
                "by_status": {},
                "oldest_record": None,
                "newest_record": None,
            }

        # Convert to PyArrow table
        arrow_table = dt.to_pyarrow_table()

        # Filter by pipeline
        import pyarrow.compute as pc

        mask = pc.equal(arrow_table["pipeline"], pipeline)
        filtered_table = arrow_table.filter(mask)

        if len(filtered_table) == 0:
            return {
                "total_records": 0,
                "by_error_code": {},
                "by_status": {},
                "oldest_record": None,
                "newest_record": None,
            }

        # Convert to pandas for easier aggregation
        df = filtered_table.to_pandas()

        # Calculate stats
        stats = {
            "total_records": len(df),
            "by_error_code": df["error_code"].value_counts().to_dict(),
            "by_status": df["dq_status"].value_counts().to_dict(),
            "oldest_record": df["ingestion_ts"].min(),
            "newest_record": df["ingestion_ts"].max(),
        }

        return stats

    def _calculate_hash(self, payload_json: str) -> str:
        """Calculate SHA256 hash of payload for deduplication.

        Args:
            payload_json: JSON string of payload

        Returns:
            Hex digest of SHA256 hash
        """
        return hashlib.sha256(payload_json.encode("utf-8")).hexdigest()
