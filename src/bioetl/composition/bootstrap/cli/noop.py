"""Centralized NoOp dependency factory functions for CLI bootstrap.

Contains pure factory functions for creating NoOp implementations used by
CLI-specific bootstrap functions. These provide silent/null implementations
for observability dependencies when full observability is not needed.

Usage:
    # In CLI bootstrap modules
    from bioetl.composition.bootstrap.cli.noop import create_noop_logger

    logger = create_noop_logger()

Design Decisions:
    - Pure functions, not singletons or factory objects
    - Each call creates a new instance (no hidden state sharing)
    - CLI-specific: warn_on_use=False for metrics (intentional opt-out)
    - MUST NOT be imported by runtime code

Note:
    This module centralizes NoOp creation to eliminate duplication across
    CLI bootstrap modules. Runtime observability uses different bootstrap
    functions from composition/bootstrap/runtime/observability.py.
"""

from __future__ import annotations

from bioetl.domain.ports.noop import (
    NoOpMetrics,
    NoOpTracing,
)
from bioetl.infrastructure.observability.noop_logger import NoOpLogger

__all__ = [
    "create_noop_logger",
    "create_noop_metrics",
    "create_noop_observability_bundle",
    "create_noop_tracing",
]


def create_noop_logger() -> NoOpLogger:
    """Create a NoOpLogger instance for CLI operations.

    Returns a logger that silently ignores all logging calls.
    Used by CLI bootstrap functions that don't require full observability.

    Returns:
        NoOpLogger instance implementing LoggerPort interface.

    Example:
        >>> logger = create_noop_logger()
        >>> logger.info("This will be silently ignored")
    """
    return NoOpLogger()


def create_noop_metrics() -> NoOpMetrics:
    """Create a NoOpMetrics instance for CLI operations.

    Returns a metrics collector that silently ignores all metrics.
    Uses warn_on_use=False since CLI intentionally opts out of metrics.

    Returns:
        NoOpMetrics adapter-facing implementation (satisfies MetricsPort).

    Example:
        >>> metrics = create_noop_metrics()
        >>> metrics.increment_counter("test", 1, {"label": "value"})
    """
    return NoOpMetrics(warn_on_use=False)


def create_noop_tracing() -> NoOpTracing:
    """Create a NoOpTracing instance for CLI operations.

    Returns a tracer that does nothing when spans are created.
    Used when distributed tracing is not needed for CLI commands.

    Returns:
        NoOpTracing adapter-facing implementation (satisfies TracingPort).

    Example:
        >>> tracing = create_noop_tracing()
        >>> tracer = tracing.get_tracer("cli")
        >>> with tracer.start_as_current_span("operation"):
        ...     pass  # Span is silently ignored
    """
    return NoOpTracing()


def create_noop_observability_bundle() -> tuple[NoOpLogger, NoOpMetrics, NoOpTracing]:
    """Create a complete NoOp observability bundle for CLI operations.

    Convenience function that creates all three NoOp implementations
    in a single call. Useful when a CLI bootstrap function needs
    multiple observability dependencies.

    Returns:
        Tuple of (NoOpLogger, NoOpMetrics, NoOpTracing) instances.

    Example:
        >>> logger, metrics, tracing = create_noop_observability_bundle()
        >>> # Use in service construction
        >>> service = SomeService(logger=logger, metrics=metrics)
    """
    return (
        create_noop_logger(),
        create_noop_metrics(),
        create_noop_tracing(),
    )
