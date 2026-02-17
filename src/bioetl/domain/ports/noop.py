"""No-operation implementations for observability ports.

Provides null object pattern implementations for TracingPort, MetricsPort,
and AuditPort when observability is not configured or not needed.

These implementations are in domain/ports (not infrastructure) because:
- They have no I/O or external dependencies
- They allow application layer to use defaults without importing infrastructure
- They maintain layer separation per RULES.md import matrix

Usage:
    >>> from bioetl.domain.ports.noop import NoOpTracing, NoOpMetrics, NoOpAudit
    >>> tracer = NoOpTracing()
    >>> metrics = NoOpMetrics()
    >>> audit = NoOpAudit()
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any, Self

if TYPE_CHECKING:
    from pathlib import Path
    from types import TracebackType

    from bioetl.domain.models.metadata import (
        BronzeMetadata,
        GoldMetadata,
        SilverMetadata,
    )
    from bioetl.domain.ports.audit import AuditEntry, AuditLayer
    from bioetl.domain.ports.memory import MemoryStats
    from bioetl.domain.types import RunID


class _NoOpSpan:
    """No-op span that mirrors the ``opentelemetry.trace.Span`` interface.

    This class intentionally reproduces the OTel Span API surface
    (``set_attribute``, ``set_status``, ``record_exception``, context manager)
    so that application code can use the same calling convention regardless
    of whether real tracing is enabled.  See TracingPort module docstring
    for the OTel facade rationale.
    """

    def __enter__(self) -> Self:
        """Context manager entry."""
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Context manager exit."""

    def set_attribute(self, key: str, value: Any) -> None:
        """Set span attribute (no-op)."""

    def set_status(self, status: Any) -> None:
        """Set span status (no-op)."""

    def record_exception(self, exception: Exception) -> None:
        """Record exception (no-op)."""


class _NoOpOtelTracer:
    """No-op tracer that mirrors the ``opentelemetry.trace.Tracer`` interface.

    Exposes ``start_as_current_span`` — the standard OTel entry point for
    creating spans — and returns ``_NoOpSpan`` instances.  This ensures
    application code written against the OTel calling convention works
    transparently when tracing is disabled.
    """

    def start_as_current_span(self, *_args: Any, **_kwargs: Any) -> _NoOpSpan:
        """Start a new span (no-op).

        Accepts any arguments to be compatible with OpenTelemetry tracer.

        Returns:
            A no-op span context manager.
        """
        return _NoOpSpan()


class NoOpTracing:
    """No-op implementation of TracingPort (Null Object Pattern).

    Returns ``_NoOpOtelTracer`` instances that mirror the OpenTelemetry
    ``Tracer`` API surface.  This is a deliberate design choice: all
    application code uses the OTel calling convention
    (``get_tracer → start_as_current_span → span context manager``)
    regardless of whether real tracing is active.  See ADR-022 for the
    full rationale.

    Used when distributed tracing is disabled or not configured.
    All operations are silently ignored with zero overhead.

    Implements:
        TracingPort: Domain port for distributed tracing (OTel facade).

    Example:
        >>> tracer = NoOpTracing()
        >>> otel_tracer = tracer.get_tracer("bioetl.transformer")
        >>> with otel_tracer.start_as_current_span("operation"):
        ...     # span is a no-op — same calling convention as real OTel
        ...     pass

    """

    def get_tracer(self, _name: str) -> _NoOpOtelTracer:
        """Get a no-op tracer.

        Args:
            _name: Tracer name (ignored).

        Returns:
            A no-op OpenTelemetry tracer.

        """
        return _NoOpOtelTracer()

    def close(self) -> None:
        """No-op close. Idempotent."""


class NoOpMetrics:
    """No-op implementation of MetricsPort.

    All operations are silently ignored. Supports optional warn_on_use
    flag for composition/CLI layers to alert when metrics are disabled.
    """

    _warned: bool = False

    def __init__(self, warn_on_use: bool = False) -> None:
        """Initialize NoOpMetrics.

        Args:
            warn_on_use: Whether to warn about disabled metrics.

        """
        if warn_on_use and not NoOpMetrics._warned:
            import warnings

            warnings.warn(
                "NoOpMetrics is being used - metrics are NOT being collected. "
                "Set BIOETL_METRICS_ENABLED=true or inject PrometheusMetrics "
                "to enable metrics collection.",
                UserWarning,
                stacklevel=2,
            )
            NoOpMetrics._warned = True

    @classmethod
    def reset_warning(cls) -> None:
        """Reset warning state (for testing)."""
        cls._warned = False

    def observe_histogram(
        self, name: str, value: float, labels: dict[str, str]
    ) -> None:
        """Observe a value for a histogram metric (no-op)."""

    def increment_counter(self, name: str, value: int, labels: dict[str, str]) -> None:
        """Increment a counter metric (no-op)."""

    def set_gauge(self, name: str, value: float, labels: dict[str, str]) -> None:
        """Set a gauge metric to a specific value (no-op)."""

    def close(self) -> None:
        """No-op close. Idempotent."""


class NoOpAudit:
    """No-op implementation of AuditPort.

    Used when audit logging is disabled or not configured.
    All operations are silently ignored.

    Implements:
        AuditPort: Domain port for audit logging.

    Example:
        >>> audit = NoOpAudit()
        >>> await audit.log_write(entry)  # no-op
        >>> entries = await audit.get_entries()  # returns []

    """

    async def log_write(self, entry: AuditEntry) -> None:
        """Log a write operation (no-op).

        Args:
            entry: The audit entry (ignored).

        """

    async def get_entries(
        self,
        run_id: RunID | None = None,  # noqa: ARG002
        layer: AuditLayer | None = None,  # noqa: ARG002
        table_name: str | None = None,  # noqa: ARG002
        start_time: datetime | None = None,  # noqa: ARG002
        end_time: datetime | None = None,  # noqa: ARG002
        limit: int = 100,  # noqa: ARG002
    ) -> list[AuditEntry]:
        """Query audit entries (no-op, returns empty list).

        Args:
            run_id: Filter by pipeline run ID (ignored).
            layer: Filter by Medallion layer (ignored).
            table_name: Filter by target table name (ignored).
            start_time: Filter entries after this time (ignored).
            end_time: Filter entries before this time (ignored).
            limit: Maximum number of entries to return (ignored).

        Returns:
            Empty list.

        """
        return []

    async def aclose(self) -> None:
        """No-op close. Idempotent."""


class NoOpPiiHasher:
    """No-op implementation of PiiHasherPort.

    Used when PII hashing is disabled or for testing.
    Returns input values unchanged (ONLY for testing purposes).

    WARNING: This implementation does NOT hash values. Use only for:
    - Unit tests where hashing is not the focus
    - Development with non-PII test data

    For production, use Sha256PiiHasher from infrastructure.security.

    Implements:
        PiiHasherPort: Domain port for PII hashing.

    Example:
        >>> hasher = NoOpPiiHasher()
        >>> hasher.hash_value("test")  # Returns unchanged
        'test'
        >>> hasher.hash_list(["a", "b"])
        ['a', 'b']

    """

    def hash_value(self, value: str | None) -> str | None:
        """Return value unchanged (no-op).

        Args:
            value: The value (returned unchanged).

        Returns:
            Input value unchanged.

        """
        return value

    def hash_list(self, values: list[str] | None) -> list[str] | None:
        """Return values unchanged (no-op).

        Args:
            values: The values (returned unchanged).

        Returns:
            Input values unchanged.

        """
        return values

    def get_salt_id(self) -> str:
        """Return placeholder salt ID.

        Returns:
            "noop" as salt identifier.

        """
        return "noop"


class NoOpMemoryMonitor:
    """No-op implementation of MemoryMonitorPort.

    Used when memory monitoring is disabled or for testing.
    Returns conservative default values indicating no memory pressure.

    Implements:
        MemoryMonitorPort: Domain port for memory monitoring.

    Example:
        >>> monitor = NoOpMemoryMonitor()
        >>> stats = monitor.get_memory_stats()
        >>> assert not stats.is_under_pressure
        >>> assert monitor.get_recommended_batch_size(1000) == 1000

    """

    def get_memory_stats(self) -> MemoryStats:
        """Return conservative memory stats (50% usage).

        Returns:
            MemoryStats with 50% memory usage (safe default).

        """
        from bioetl.domain.ports.memory import MemoryStats

        return MemoryStats(
            used_mb=4096.0,
            available_mb=4096.0,
            total_mb=8192.0,
            percent_used=0.5,
            process_mb=256.0,
        )

    def is_under_pressure(self) -> bool:
        """Return False (no memory pressure).

        Returns:
            False, indicating no memory pressure.

        """
        return False

    def get_recommended_batch_size(self, current_batch_size: int) -> int:
        """Return current batch size (no reduction needed).

        Args:
            current_batch_size: Current batch size.

        Returns:
            Unchanged batch size.

        """
        return current_batch_size

    def estimate_batch_memory_mb(
        self,
        record_count: int,
        avg_record_size_bytes: int = 1024,
    ) -> float:
        """Estimate memory usage for a batch.

        Args:
            record_count: Number of records in batch.
            avg_record_size_bytes: Average size per record in bytes.

        Returns:
            Estimated memory usage in MB.

        """
        overhead_factor = 2.5
        return (record_count * avg_record_size_bytes * overhead_factor) / (1024 * 1024)

    def calculate_max_batch_size(self, _avg_record_size_bytes: int = 1024) -> int:
        """Return a high max batch size (no constraints).

        Args:
            _avg_record_size_bytes: Average size per record in bytes (unused).

        Returns:
            Large max batch size (10000).

        """
        return 10000


class NoOpMetadataWriter:
    """No-op implementation of MetadataWriterPort.

    Used when save_metadata is disabled or for testing.
    All operations are silently ignored and return empty strings.

    Implements:
        MetadataWriterPort: Domain port for metadata sidecar files.

    Example:
        >>> writer = NoOpMetadataWriter()
        >>> await writer.write_bronze_metadata(path, metadata)  # returns ""
        ''

    """

    async def write_bronze_metadata(
        self,
        base_path: str | Path,  # noqa: ARG002
        metadata: BronzeMetadata,  # noqa: ARG002
        *,
        provider: str | None = None,  # noqa: ARG002
        entity: str | None = None,  # noqa: ARG002
    ) -> str:
        """Write Bronze metadata (no-op).

        Args:
            base_path: Base path (ignored).
            metadata: Metadata (ignored).
            provider: Provider name (ignored).
            entity: Entity type (ignored).

        Returns:
            Empty string.

        """
        return ""

    async def write_silver_metadata(
        self,
        base_path: str | Path,  # noqa: ARG002
        metadata: SilverMetadata,  # noqa: ARG002
        *,
        table_name: str | None = None,  # noqa: ARG002
        flat_structure: bool = False,  # noqa: ARG002
        provider: str | None = None,  # noqa: ARG002
        entity: str | None = None,  # noqa: ARG002
    ) -> str:
        """Write Silver metadata (no-op).

        Args:
            base_path: Base path (ignored).
            metadata: Metadata (ignored).
            table_name: Table name (ignored).
            flat_structure: Flat structure flag (ignored).
            provider: Provider name (ignored).
            entity: Entity type (ignored).

        Returns:
            Empty string.

        """
        return ""

    async def write_gold_metadata(
        self,
        base_path: str | Path,  # noqa: ARG002
        metadata: GoldMetadata,  # noqa: ARG002
        *,
        table_name: str | None = None,  # noqa: ARG002
        flat_structure: bool = False,  # noqa: ARG002
        provider: str | None = None,  # noqa: ARG002
        entity: str | None = None,  # noqa: ARG002
    ) -> str:
        """Write Gold metadata (no-op).

        Args:
            base_path: Base path (ignored).
            metadata: Metadata (ignored).
            table_name: Table name (ignored).
            flat_structure: Flat structure flag (ignored).
            provider: Provider name (ignored).
            entity: Entity type (ignored).

        Returns:
            Empty string.

        """
        return ""

    async def aclose(self) -> None:
        """No-op close. Idempotent."""
