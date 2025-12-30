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
    from types import TracebackType

    from bioetl.domain.ports.audit import AuditEntry, AuditLayer
    from bioetl.domain.types import RunID


class _NoOpSpan:
    """No-op span that does nothing.

    Implements the span interface used by OpenTelemetry tracers.
    Supports context manager protocol for use with `with` statements.
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
        pass

    def set_attribute(self, key: str, value: Any) -> None:
        """Set span attribute (no-op)."""
        pass

    def set_status(self, status: Any) -> None:
        """Set span status (no-op)."""
        pass

    def record_exception(self, exception: Exception) -> None:
        """Record exception (no-op)."""
        pass


class _NoOpOtelTracer:
    """No-op OpenTelemetry tracer.

    Returns _NoOpSpan instances that implement the span interface.
    """

    def start_as_current_span(self, *_args: Any, **_kwargs: Any) -> _NoOpSpan:
        """Start a new span (no-op).

        Accepts any arguments to be compatible with OpenTelemetry tracer.

        Returns:
            A no-op span context manager.
        """
        return _NoOpSpan()


class NoOpTracing:
    """No-op implementation of TracingPort.

    Used when distributed tracing is disabled or not configured.
    All operations are silently ignored.

    Implements:
        TracingPort: Domain port for distributed tracing.

    Example:
        >>> tracer = NoOpTracing()
        >>> otel_tracer = tracer.get_tracer("bioetl.transformer")
        >>> with otel_tracer.start_as_current_span("operation"):
        ...     # span is a no-op
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
        pass


class NoOpMetrics:
    """No-op implementation of MetricsPort.

    Used when metrics collection is disabled or not configured.
    All operations are silently ignored.

    Implements:
        MetricsPort: Domain port for metrics collection.

    Example:
        >>> metrics = NoOpMetrics()
        >>> metrics.observe_histogram("duration", 1.5, {"entity": "activity"})
        >>> metrics.increment_counter("errors", 1, {"type": "validation"})

    """

    def observe_histogram(
        self,
        name: str,
        value: float,
        labels: dict[str, str],
    ) -> None:
        """Observe a value for a histogram metric (no-op).

        Args:
            name: The name of the histogram metric.
            value: The value to observe.
            labels: A dictionary of label names to label values.

        """
        pass

    def increment_counter(
        self,
        name: str,
        value: int,
        labels: dict[str, str],
    ) -> None:
        """Increment a counter metric (no-op).

        Args:
            name: The name of the counter metric.
            value: The amount to increment by.
            labels: A dictionary of label names to label values.

        """
        pass

    def set_gauge(
        self,
        name: str,
        value: float,
        labels: dict[str, str],
    ) -> None:
        """Set a gauge metric to a specific value (no-op).

        Args:
            name: The name of the gauge metric.
            value: The value to set.
            labels: A dictionary of label names to label values.

        """
        pass

    def close(self) -> None:
        """No-op close. Idempotent."""
        pass


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
        pass

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
        pass


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

    def get_memory_stats(self) -> "MemoryStats":
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

    def calculate_max_batch_size(self, avg_record_size_bytes: int = 1024) -> int:
        """Return a high max batch size (no constraints).

        Args:
            avg_record_size_bytes: Average size per record in bytes.

        Returns:
            Large max batch size (10000).

        """
        return 10000
