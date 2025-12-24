"""Port interfaces (Protocols) for dependency inversion.

Implements RULES.md §1.1 - Ports & Adapters architecture.
These interfaces define contracts for external systems like data sources,
storage, and other infrastructure components. Each port is defined as a
Protocol, allowing for structural subtyping (duck typing) and clear
separation of concerns between the domain and infrastructure layers.
"""

from collections.abc import AsyncIterator, Iterator
from datetime import datetime
from typing import Any, Literal, Protocol, Self, runtime_checkable

from bioetl.domain.filter_config import FilterLoadResult
from bioetl.domain.types import (
    ArrowSchema,
    BatchID,
    HealthStatus,
    RunID,
    RunType,
    ValidationResult,
)


@runtime_checkable
class TracingPort(Protocol):
    """Port for distributed tracing (OpenTelemetry).

    Abstracts the tracer implementation to allow no-op or specific backends.
    """

    def get_tracer(self, name: str) -> Any:
        """Get a tracer instance for instrumentation."""
        ...


@runtime_checkable
class DataSourcePort(Protocol):
    """
    Port for data sources (e.g., ChEMBL, PubChem).

    This interface abstracts the process of fetching data from an external
    source, allowing the application to be independent of the specific
    implementation of the data source client.
    """

    @property
    def provider_name(self) -> str:
        """The unique name of the data provider (e.g., 'chembl')."""
        ...

    async def __aenter__(self) -> Self:
        """Enter the async context manager."""
        ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        """Exit the async context manager."""
        ...

    def fetch(
        self,
        entity_type: str,
        limit: int | None = None,
        query: str | None = None,
        filter_ids: list[str] | None = None,
        filter_field: str | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """
        Fetch records from the data source (async generator).

        Note: This is NOT an async def because async generator functions
        return AsyncIterator directly without needing to be awaited.
        Implementations should be async generators (async def with yield).

        Args:
            entity_type: The type of entity to fetch (e.g., 'activity', 'molecule').
            limit: The maximum number of records to fetch.
            query: Optional search query for providers that support it (e.g., PubChem, UniProt).
            filter_ids: Optional set of IDs to filter by (for adapters that support filtering).
            filter_field: Optional field name to filter on (for adapters that support filtering).

        Yields:
            A dictionary representing a single record from the data source.
        """
        ...

    async def health_check(self) -> HealthStatus:
        """
        Check the health of the data source.

        Returns:
            A HealthStatus object indicating the current status of the source.
        """
        ...

    async def aclose(self) -> None:
        """Gracefully close the data source and release resources."""
        ...


@runtime_checkable
class InputFilterPort(Protocol):
    """Port for loading filter IDs from external sources.

    This interface abstracts the process of reading filter IDs from
    various sources (CSV files, databases, etc.) for filtering API requests.
    """

    async def load_filter_ids(
        self,
        source_path: str,
        column_name: str,
    ) -> FilterLoadResult:
        """Load unique IDs from an external source.

        IDs are returned in sorted order for deterministic processing.
        Includes metadata about duplicates found in the source.

        Args:
            source_path: Path to the filter source (e.g., CSV file path).
            column_name: Name of the column containing filter IDs.

        Returns:
            FilterLoadResult with sorted unique IDs and duplicate statistics.

        Raises:
            FileNotFoundError: If the source file does not exist.
            ValueError: If the column is not found in the source.
        """
        ...


@runtime_checkable
class StoragePort(Protocol):
    """
    Port for data storage (Bronze, Silver, Gold layers).

    This interface abstracts the underlying storage mechanism (e.g., file system,
    data lake, data warehouse), allowing the application to write data to
    different layers without knowing the implementation details.
    """

    async def write_bronze(
        self,
        records: Iterator[bytes],
        provider: str,
        entity: str,
        date: datetime,
        batch_id: BatchID,
        run_id: RunID,
        run_type: RunType,
    ) -> None:
        """
        Write raw records to the Bronze layer.

        Args:
            records: An iterable of byte strings, where each string is a raw record.
            provider: The name of the data provider.
            entity: The type of entity being written.
            date: The datetime for the data partition.
            batch_id: The unique identifier for the batch of records.
            run_id: The unique identifier for the pipeline run (for traceability).
            run_type: The type of pipeline run (incremental, backfill, rebuild).
        """
        ...

    async def write_silver(
        self,
        table_name: str,
        records: list[dict[str, Any]],
        primary_keys: list[str],
        schema: ArrowSchema,
        mode: Literal["merge", "append", "delete"] = "merge",
        partition_cols: list[str] | None = None,
    ) -> None:
        """
        Write transformed records to the Silver layer.

        Args:
            table_name: The name of the table to write to.
            records: A list of dictionaries, where each dictionary is a transformed record.
            primary_keys: A list of column names that form the primary key.
            schema: The PyArrow schema definition for the records (ArrowSchema alias).
            mode: The write mode (e.g., 'merge', 'append', 'delete').
            partition_cols: Optional list of columns to partition by.
        """
        ...

    async def write_gold(
        self,
        table_name: str,
        records: list[dict[str, Any]],
        primary_keys: list[str] | None = None,
        mode: Literal["overwrite", "append", "scd2"] = "overwrite",
    ) -> None:
        """
        Write aggregated or validated records to the Gold layer.

        Args:
            table_name: The name of the table to write to.
            records: A list of dictionaries, where each dictionary is a gold record.
            primary_keys: Optional list of column names for sorting/deduplication.
            mode: The write mode (e.g., 'overwrite', 'append', 'scd2').
        """
        ...

    def clear_silver(self, table_name: str) -> int:
        """
        Clear Silver layer data for a specific table.

        Clears both Delta tables and CSV exports (if configured).
        Should only be called for rebuild/backfill runs, NOT for incremental.

        Args:
            table_name: The name of the table to clear.

        Returns:
            Count of cleared items (tables + files).
        """
        ...

    def clear_gold(self, table_name: str) -> int:
        """
        Clear Gold layer data for a specific table.

        Clears both Delta tables and CSV exports (if configured).
        Should only be called for rebuild/backfill runs, NOT for incremental.

        Args:
            table_name: The name of the table to clear.

        Returns:
            Count of cleared items (tables + files).
        """
        ...

    async def aclose(self) -> None:
        """Gracefully close the storage connection and release resources."""
        ...

    def clear_csv(self, table_name: str | None = None) -> int:
        """Clear CSV export files for Silver and Gold layers.

        Should be called at the start of a pipeline run to ensure
        fresh CSV exports without duplicates from previous runs.

        Args:
            table_name: If provided, only clear CSV for this table.
                       If None, clear all CSV files.

        Returns:
            Total number of files deleted.
        """
        ...

    def clear_delta(self, table_name: str | None = None) -> int:
        """Clear Delta tables for Silver and Gold layers.

        Should be called at the start of a pipeline run to ensure
        fresh data without duplicates from previous runs.

        Args:
            table_name: If provided, only clear Delta table for this table.
                       If None, clear all Delta tables.

        Returns:
            Total number of tables cleared.
        """
        ...


@runtime_checkable
class LockPort(Protocol):
    """
    Port for distributed locking.

    This interface provides a mechanism for coordinating operations across
    multiple instances or processes, preventing race conditions.
    """

    async def acquire(
        self,
        key: str,
        owner_id: RunID,
        ttl: int | None = None,
        wait: bool = False,
        wait_timeout: int = 300,
        exclusive: bool = False,
    ) -> bool:
        """
        Acquire a lock.

        Args:
            key: The unique key for the lock.
            owner_id: The ID of the run attempting to acquire the lock.
            ttl: Time-to-live for the lock in seconds.
            wait: If True, wait for the lock to be released if it's already held.
            wait_timeout: Maximum time to wait for the lock in seconds.
            exclusive: If True, acquire an exclusive lock.

        Returns:
            True if the lock was acquired, False otherwise.
        """
        ...

    async def release(
        self,
        key: str,
        owner_id: RunID,
        exclusive: bool = False,
    ) -> bool:
        """
        Release a lock.

        Args:
            key: The unique key for the lock.
            owner_id: The ID of the run releasing the lock.
            exclusive: If True, release an exclusive lock.

        Returns:
            True if the lock was released, False otherwise.
        """
        ...

    async def heartbeat(
        self,
        key: str,
        owner_id: RunID,
        exclusive: bool = False,
    ) -> bool:
        """
        Refresh a lock's TTL to prevent it from expiring.

        Args:
            key: The unique key for the lock.
            owner_id: The ID of the run refreshing the lock.
            exclusive: If True, refresh an exclusive lock.

        Returns:
            True if the heartbeat was successful, False otherwise.
        """
        ...

    async def aclose(self) -> None:
        """Gracefully close the lock connection and release resources."""
        ...


@runtime_checkable
class CheckpointPort(Protocol):
    """
    Port for pipeline checkpointing.

    This interface allows pipelines to save and load their state, enabling
    resilience and run tracking.
    """

    async def save(
        self,
        pipeline: str,
        run_id: RunID,
        metadata: dict[str, Any],
    ) -> None:
        """
        Save a checkpoint.

        Args:
            pipeline: The name of the pipeline.
            run_id: The ID of the run creating the checkpoint.
            metadata: Additional metadata to store with the checkpoint.
        """
        ...

    async def load(
        self,
        pipeline: str,
    ) -> tuple[RunID, dict[str, Any]] | None:
        """
        Load a checkpoint.

        Args:
            pipeline: The name of the pipeline.

        Returns:
            A tuple containing the run ID and metadata, or None
            if no checkpoint is found.
        """
        ...

    async def list_all(self) -> list[str]:
        """
        List all pipelines that have checkpoints.

        Returns:
            A list of pipeline names.
        """
        ...

    async def delete(self, pipeline: str) -> None:
        """
        Delete a checkpoint.

        Args:
            pipeline: The name of the pipeline whose checkpoint should be deleted.
        """
        ...

    async def aclose(self) -> None:
        """Gracefully close the checkpoint connection and release resources."""
        ...


@runtime_checkable
class QuarantinePort(Protocol):
    """
    Port for quarantining failed records.

    This interface provides a way to isolate records that fail processing
    for later analysis, preventing them from stopping the entire pipeline.
    """

    async def write(
        self,
        pipeline: str,
        error_code: str,
        payload: dict[str, Any],
        bronze_batch_id: BatchID,
        run_id: RunID | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """
        Write a record to quarantine.

        Args:
            pipeline: The name of the pipeline where the error occurred.
            error_code: A code identifying the type of error.
            payload: The record that failed processing.
            bronze_batch_id: The ID of the bronze batch containing the record.
            run_id: Optional ID of the pipeline run for traceability.
            metadata: Optional additional metadata (e.g., error_details, bronze_file_uri).
        """
        ...

    async def inspect(
        self,
        pipeline: str,
        limit: int = 10,
        error_code: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Inspect records in quarantine.

        Args:
            pipeline: The name of the pipeline to inspect.
            limit: The maximum number of records to return.
            error_code: Filter records by a specific error code.

        Returns:
            A list of quarantined records.
        """
        ...

    async def get_stats(self, pipeline: str) -> dict[str, Any]:
        """
        Get statistics about the quarantined records for a pipeline.

        Args:
            pipeline: The name of the pipeline.

        Returns:
            A dictionary of statistics (e.g., count by error code).
        """
        ...

    async def aclose(self) -> None:
        """Gracefully close the quarantine connection and release resources."""
        ...


@runtime_checkable
class MetricsPort(Protocol):
    """
    Port for metrics collection.

    This interface abstracts the metrics collection mechanism, allowing the
    application to record metrics without knowing the specific implementation
    (e.g., Prometheus, StatsD, CloudWatch).

    Note: MetricsPort uses synchronous methods for low-overhead operations.
    Unlike I/O ports, metric collection should be fast and non-blocking
    by design (using thread-safe counters, not I/O).
    """

    def observe_histogram(
        self,
        name: str,
        value: float,
        labels: dict[str, str],
    ) -> None:
        """
        Observe a value for a histogram metric.

        Args:
            name: The name of the histogram metric.
            value: The value to observe.
            labels: A dictionary of label names to label values.
        """
        ...

    def increment_counter(
        self,
        name: str,
        value: int,
        labels: dict[str, str],
    ) -> None:
        """
        Increment a counter metric.

        Args:
            name: The name of the counter metric.
            value: The amount to increment by.
            labels: A dictionary of label names to label values.
        """
        ...


@runtime_checkable
class LoggerPort(Protocol):
    """Port for structured logging.

    This interface abstracts the logging mechanism, allowing the application
    to log messages without depending on a specific logging library
    (e.g., structlog, loguru, stdlib logging).

    Note: LoggerPort uses synchronous methods as logging operations
    should be fast and non-blocking by design.
    """

    def bind(self, **kwargs: Any) -> Self:
        """Bind additional context to the logger.

        Returns a new logger instance with the bound context.
        """
        ...

    def info(self, event: str, **kwargs: Any) -> Any:
        """Log an informational message."""
        ...

    def warning(self, event: str, **kwargs: Any) -> Any:
        """Log a warning message."""
        ...

    def error(self, event: str, **kwargs: Any) -> Any:
        """Log an error message."""
        ...

    def debug(self, event: str, **kwargs: Any) -> Any:
        """Log a debug message."""
        ...

    def exception(self, event: str, **kwargs: Any) -> Any:
        """Log an exception with traceback."""
        ...


@runtime_checkable
class GoldValidatorPort(Protocol):
    """Port for Gold layer record validation.

    This interface abstracts the validation mechanism for Gold records,
    allowing different validation strategies (Pandera, Great Expectations, etc.)
    to be injected without coupling RecordProcessor to a specific implementation.

    Note: GoldValidatorPort uses synchronous methods as validation
    should be a CPU-bound operation without I/O.
    """

    def validate(self, records: list[dict[str, Any]]) -> ValidationResult:
        """Validate records for Gold layer.

        Args:
            records: List of record dictionaries to validate.

        Returns:
            ValidationResult with valid flag and any error messages.
        """
        ...


__all__ = [
    "CheckpointPort",
    "DataSourcePort",
    "GoldValidatorPort",
    "InputFilterPort",
    "LockPort",
    "LoggerPort",
    "MetricsPort",
    "QuarantinePort",
    "StoragePort",
]
