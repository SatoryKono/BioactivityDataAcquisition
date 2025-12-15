"""Port interfaces (Protocols) for dependency inversion.

Implements RULES.md §1.1 - Ports & Adapters architecture.
All interfaces use typing.Protocol for structural typing.

Requirements:
- REQ-ARCH-001: Ports defined via typing.Protocol
- REQ-ARCH-004: Critical adapters use @runtime_checkable

Type checking enforced by mypy --strict (REQ-ARCH-002).
"""

from collections.abc import Iterator
from datetime import datetime
from pathlib import Path
from typing import Any, Protocol

from .types import (
    BatchID,
    ContentHash,
    EntityID,
    HealthStatus,
    RunID,
    RunType,
    Watermark,
)


# =============================================================================
# Data Source Ports
# =============================================================================


class DataSourcePort(Protocol):
    """Interface for external data providers (ChEMBL, PubChem, etc).

    Adapters: src/bioetl/infrastructure/adapters/{provider}/
    """

    def fetch(
        self,
        entity_type: str,
        watermark: Watermark | None = None,
        limit: int | None = None,
    ) -> Iterator[dict[str, Any]]:
        """Fetch records from data source.

        Args:
            entity_type: Type of entity (activity, compound, target, etc)
            watermark: Last checkpoint for incremental load (None = full load)
            limit: Maximum number of records (None = no limit)

        Yields:
            Raw records as dictionaries

        Raises:
            AuthError: Authentication failed (401, 403)
            RateLimitError: Rate limit exceeded (429)
            NetworkError: Connection issues (502, 504, timeout)
        """
        ...

    def health_check(self) -> HealthStatus:
        """Check provider health status.

        Returns:
            HEALTHY: operational (0 errors)
            DEGRADED: issues detected (1-2 errors)
            UNHEALTHY: down (≥3 errors)
        """
        ...

    @property
    def provider_name(self) -> str:
        """Provider identifier (chembl, pubchem, uniprot, etc)."""
        ...


# =============================================================================
# Storage Ports
# =============================================================================


class StoragePort(Protocol):
    """Interface for data storage (S3, Delta Lake)."""

    def write_bronze(
        self,
        records: Iterator[bytes],
        provider: str,
        entity: str,
        date: datetime,
        batch_id: BatchID,
    ) -> Path:
        """Write raw records to Bronze layer (JSONL + zstd).

        Path format: bronze/v1/{provider}/{entity}/{date}/

        Args:
            records: Iterator of JSONL records (bytes)
            provider: Provider name
            entity: Entity type
            date: Ingestion date
            batch_id: Unique batch identifier

        Returns:
            Path to written file

        Requirements:
            - REQ-DATA-001: JSONL + zstd format
            - REQ-DATA-002: Path format bronze/{version}/{provider}/{entity}/{date}/
            - REQ-DATA-003: Append-only writes
        """
        ...

    def write_silver(
        self,
        table_name: str,
        records: list[dict[str, Any]],
        primary_keys: list[str],
        partition_cols: list[str] | None = None,
    ) -> None:
        """Write normalized records to Silver layer (Delta Lake merge/upsert).

        Args:
            table_name: Silver table name (e.g., 'chembl.activity')
            records: List of normalized records with metadata (_run_id, _run_type, etc)
            primary_keys: Keys for merge operation (e.g., ['entity_id'])
            partition_cols: Partition columns (e.g., ['year', 'month'])

        Requirements:
            - REQ-DATA-006: Delta Lake format (ACID)
            - REQ-DATA-008: Merge/Upsert strategy
            - REQ-LINEAGE-001: Records contain _source_batch_id
        """
        ...

    def write_gold(
        self,
        table_name: str,
        records: list[dict[str, Any]],
        mode: str = "overwrite",
    ) -> None:
        """Write validated records to Gold layer.

        Args:
            table_name: Gold table name
            records: Strictly validated records
            mode: Write mode ('overwrite' or 'append')

        Requirements:
            - REQ-DATA-009: Strict validation (strict=True)
            - REQ-DATA-010: SCD Type 2 or date partitioning
        """
        ...


# =============================================================================
# Lock Port (Distributed Coordination)
# =============================================================================


class LockPort(Protocol):
    """Interface for distributed locking (Redis).

    Requirements from RULES.md §3.3:
    - TTL: 60 seconds
    - Heartbeat: every 20 seconds
    - Max duration: 4 hours
    - Fencing token: owner_id (run_id)
    """

    def acquire(
        self,
        key: str,
        owner_id: RunID,
        ttl: int = 60,
        wait: bool = False,
        wait_timeout: int = 300,
    ) -> bool:
        """Acquire distributed lock.

        Args:
            key: Lock key (e.g., 'lock:chembl_activity')
            owner_id: Run ID of lock owner (fencing token)
            ttl: Time-to-live in seconds
            wait: Wait for lock if unavailable
            wait_timeout: Maximum wait time (seconds)

        Returns:
            True if lock acquired, False otherwise

        Requirements:
            - REQ-LOCK-001: Redis SETNX + EXPIRE
            - REQ-LOCK-002: TTL 60 seconds
            - REQ-LOCK-005: Fencing token (owner_id)
        """
        ...

    def release(self, key: str, owner_id: RunID) -> bool:
        """Release lock.

        Args:
            key: Lock key
            owner_id: Run ID of lock owner (must match)

        Returns:
            True if released, False if not owned

        Requirements:
            - REQ-LOCK-008: Validate owner_id before release
        """
        ...

    def heartbeat(self, key: str, owner_id: RunID) -> bool:
        """Refresh lock TTL (keep-alive).

        Args:
            key: Lock key
            owner_id: Run ID of lock owner (must match)

        Returns:
            True if heartbeat successful, False if lock lost

        Requirements:
            - REQ-LOCK-003: Heartbeat every 20 seconds
            - REQ-LOCK-007: Fail immediately if heartbeat fails
        """
        ...

    def is_locked(self, key: str) -> bool:
        """Check if lock exists."""
        ...

    def get_owner(self, key: str) -> RunID | None:
        """Get current lock owner ID."""
        ...


# =============================================================================
# Checkpoint Port (State Persistence)
# =============================================================================


class CheckpointPort(Protocol):
    """Interface for checkpoint storage (S3 or DB).

    Requirements from RULES.md §5.3.1:
    - Atomic writes (If-Match/ETag for S3)
    - Recovery on --resume flag
    - Cleanup after successful run
    """

    def save(
        self,
        pipeline: str,
        watermark: Watermark,
        run_id: RunID,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Save checkpoint.

        Args:
            pipeline: Pipeline name
            watermark: Checkpoint value (timestamp, ID, offset)
            run_id: Current run ID
            metadata: Optional metadata

        Requirements:
            - REQ-SHUTDOWN-003: Atomic save with If-Match/ETag
        """
        ...

    def load(self, pipeline: str) -> tuple[Watermark, RunID, dict[str, Any]] | None:
        """Load last checkpoint.

        Args:
            pipeline: Pipeline name

        Returns:
            (watermark, run_id, metadata) if exists, None otherwise

        Requirements:
            - REQ-CHECKPOINT-001: Check existence on startup
        """
        ...

    def delete(self, pipeline: str) -> None:
        """Delete checkpoint (after successful run).

        Requirements:
            - REQ-CHECKPOINT-004: Delete after success
        """
        ...


# =============================================================================
# Quarantine Port (Dead Letter Queue)
# =============================================================================


class QuarantinePort(Protocol):
    """Interface for quarantine storage (unified table).

    Requirements from RULES.md §2.6:
    - Unified table: common.quarantine
    - Payload truncated to 64KB
    - Retention: 30 days
    - Linkage to Bronze via bronze_file_uri or batch_id
    """

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

        Args:
            pipeline: Pipeline name
            error_code: Error type (SCHEMA_VIOLATION, INVALID_DATA, etc)
            payload: Raw record (will be truncated to 64KB)
            bronze_batch_id: Reference to Bronze batch
            bronze_file_uri: Full S3 path to Bronze file
            error_details: Additional error context

        Returns:
            Content hash for deduplication

        Requirements:
            - REQ-QUARANTINE-001: Unified table common.quarantine
            - REQ-QUARANTINE-002: Payload truncated to 64KB
            - REQ-QUARANTINE-004: Link to Bronze
        """
        ...

    def inspect(
        self,
        pipeline: str,
        limit: int = 100,
        error_code: str | None = None,
    ) -> list[dict[str, Any]]:
        """Inspect quarantine records.

        Args:
            pipeline: Pipeline name
            limit: Maximum records to return
            error_code: Filter by error code

        Returns:
            List of quarantine records
        """
        ...

    def replay(
        self,
        pipeline: str,
        error_code: str | None = None,
        max_age_days: int = 7,
    ) -> Iterator[dict[str, Any]]:
        """Replay quarantine records for reprocessing.

        Args:
            pipeline: Pipeline name
            error_code: Filter by error code
            max_age_days: Only replay records newer than this

        Yields:
            Quarantine records ready for reprocessing
        """
        ...

    def purge(self, pipeline: str, older_than_days: int = 30) -> int:
        """Purge old quarantine records.

        Args:
            pipeline: Pipeline name
            older_than_days: Delete records older than this

        Returns:
            Number of deleted records

        Requirements:
            - REQ-QUARANTINE-003: 30-day retention
        """
        ...


# =============================================================================
# Lineage Port (Data Provenance)
# =============================================================================


class LineagePort(Protocol):
    """Interface for data lineage tracking.

    Requirements from RULES.md §2.3:
    - Optimized schema: batch_id -> Bronze files
    - sys.lineage_log table
    - No full paths in Silver records
    """

    def log_batch(
        self,
        batch_id: BatchID,
        pipeline: str,
        bronze_files: list[str],
        transform_version: str,
        run_id: RunID,
        run_type: RunType,
        run_params: dict[str, Any],
        record_count: int,
        error_count: int = 0,
    ) -> None:
        """Log batch lineage.

        Args:
            batch_id: Unique batch ID
            pipeline: Pipeline name
            bronze_files: List of Bronze file S3 paths
            transform_version: Transformation code version
            run_id: Run ID
            run_type: incremental | backfill | rebuild
            run_params: Parameters used for this run
            record_count: Number of records processed
            error_count: Number of errors

        Requirements:
            - REQ-LINEAGE-002: Store in sys.lineage_log
            - REQ-LINEAGE-003: No full paths in Silver records
        """
        ...

    def get_batch_sources(self, batch_id: BatchID) -> list[str]:
        """Get Bronze file paths for a batch.

        Args:
            batch_id: Batch ID

        Returns:
            List of Bronze file S3 URIs
        """
        ...


# =============================================================================
# Metrics Port (Observability)
# =============================================================================


class MetricsPort(Protocol):
    """Interface for metrics export (Prometheus).

    Requirements from RULES.md §3.4:
    - Prometheus format with labels
    - DQ metrics: dq_validation_score, data_freshness_seconds
    - Provider health: provider_health_status, circuit_breaker_state
    """

    def record_dq_metric(
        self,
        pipeline: str,
        check: str,
        column: str,
        value: float,
    ) -> None:
        """Record data quality metric.

        Args:
            pipeline: Pipeline name
            check: Check type (null_rate, unique_count, schema_violations)
            column: Column name (or 'all' for table-level)
            value: Metric value

        Requirements:
            - REQ-DQ-002: dq_validation_score{check, column}
        """
        ...

    def record_freshness(
        self,
        pipeline: str,
        seconds: float,
    ) -> None:
        """Record data freshness (now - max(updated_at)).

        Requirements:
            - REQ-DQ-003: data_freshness_seconds
        """
        ...

    def record_provider_health(
        self,
        provider: str,
        status: HealthStatus,
    ) -> None:
        """Record provider health status.

        Requirements:
            - REQ-HEALTH-003: provider_health_status metric
        """
        ...

    def record_circuit_breaker_state(
        self,
        provider: str,
        state: int,  # 0=Closed, 1=Half-Open, 2=Open
    ) -> None:
        """Record circuit breaker state.

        Requirements:
            - REQ-CB-004: circuit_breaker_state metric
        """
        ...
