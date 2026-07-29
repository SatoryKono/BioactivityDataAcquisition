# pyright: reportImportCycles=false
# Import cycle residual tracked in allowlist (product burn-down).
"""Observability bundle for unified dependency injection.

Aggregates logger, tracer, and metrics into a single injectable dependency,
simplifying constructor signatures across the codebase.

This module enforces the Unified Observability Contract:
- logger: REQUIRED - pipeline cannot run without structured logging
- metrics: REQUIRED - always valid implementation (NoOpMetrics fallback)
- tracer: REQUIRED - explicit TracingPort owned by composition
- audit: REQUIRED - explicit AuditPort owned by composition
- dq_monitor: Optional - data quality anomaly detection
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, Protocol, cast

from bioetl.domain.ports import AuditPort, LoggerPort, MetricsPort, TracingPort

if TYPE_CHECKING:
    from bioetl.composition.runtime_builders.runner_inputs import RunnerInputs
    from bioetl.domain.ports import DQMonitorPort


class ObservabilityContractError(Exception):
    """Raised when observability contract requirements are not met.

    This error indicates a programming error in the bootstrap/composition layer
    where required observability components were not properly initialized.
    """


@dataclass(frozen=True)
class ObservabilityBundle:
    """Unified observability context for pipeline execution.

    Aggregates logger, tracer, metrics, audit, and data quality monitor into
    a single injectable dependency. This reduces the number of constructor
    parameters and ensures consistent observability configuration across components.

    Unified Observability Contract:
    - logger: REQUIRED - structured logger, cannot be None
    - metrics: REQUIRED - MetricsPort implementation (NoOpMetrics if disabled)
    - tracer: REQUIRED - distributed tracing port (use NoOpTracing if disabled)
    - audit: REQUIRED - audit sink for runtime lifecycle and storage traceability
    - dq_monitor: Optional - data quality anomaly detector

    Raises:
        ObservabilityContractError: If required components are None.

    Attributes:
        logger: Structured logger for the pipeline.
        metrics: Metrics collection port (never None - uses NoOpMetrics fallback).
        tracer: Distributed tracing port (never None - use NoOpTracing if disabled).
        audit: Audit sink for runtime lifecycle and storage traceability.
        dq_monitor: Optional data quality anomaly detector.
    """

    logger: LoggerPort
    metrics: MetricsPort
    tracer: TracingPort
    audit: AuditPort
    dq_monitor: DQMonitorPort | None = None

    def __post_init__(self) -> None:
        """Validate that required observability components are present."""
        if self.logger is None:
            raise ObservabilityContractError(
                "Logger is required. Cannot run pipeline without structured logging. "
                "Use bootstrap_observability_bundle() to create a valid bundle."
            )
        if self.metrics is None:
            raise ObservabilityContractError(
                "Metrics port is required. Use NoOpMetrics when metrics are disabled. "
                "Use bootstrap_observability_bundle() to create a valid bundle."
            )
        if self.tracer is None:
            raise ObservabilityContractError(
                "Tracer is required. Use NoOpTracing when tracing is disabled. "
                "Use bootstrap_observability_bundle() to create a valid bundle."
            )
        if self.audit is None:
            raise ObservabilityContractError(
                "Audit port is required. Use NoOpAudit when audit is disabled. "
                "Use bootstrap_observability_bundle() to create a valid bundle."
            )

    @classmethod
    def create(
        cls,
        logger: LoggerPort,
        metrics: MetricsPort,
        tracer: TracingPort,
        audit: AuditPort,
        dq_monitor: DQMonitorPort | None = None,
    ) -> ObservabilityBundle:
        """Factory method for creating observability bundle.

        Enforces the Unified Observability Contract by requiring
        valid logger and metrics implementations.

        Args:
            logger: Structured logger instance (required).
            metrics: Metrics port implementation (required, use NoOpMetrics if disabled).
            tracer: Tracer port (required, use NoOpTracing if disabled).
            audit: Audit port implementation (required, use NoOpAudit if disabled).
            dq_monitor: Optional data quality monitor port.

        Returns:
            Configured ObservabilityBundle instance.

        Raises:
            ObservabilityContractError: If any required observability dependency is None.
        """
        return cls(
            logger=logger,
            metrics=metrics,
            tracer=tracer,
            audit=audit,
            dq_monitor=dq_monitor,
        )

    def bind(self, **kwargs: object) -> ObservabilityBundle:
        """Create new bundle with bound logger context.

        Creates a new bundle with additional context bound to the logger.
        Useful for adding request-specific context (e.g., run_id, entity_id).

        Args:
            **kwargs: Key-value pairs to bind to the logger.

        Returns:
            New ObservabilityBundle with bound logger context.
        """
        return ObservabilityBundle(
            logger=self.logger.bind(**kwargs),
            tracer=self.tracer,
            metrics=self.metrics,
            audit=self.audit,
            dq_monitor=self.dq_monitor,
        )


class _LoggerBindableObservability(Protocol):
    logger: object


def bind_manifest_logger_context(
    inputs: RunnerInputs,
    manifest_id: str,
) -> RunnerInputs:
    """Bind ``manifest_id`` into a runtime observability bundle when present."""
    observability = getattr(inputs, "observability", None)
    rebound_observability = _rebind_observability_logger(
        observability=observability,
        manifest_id=manifest_id,
    )
    if rebound_observability is observability:
        return inputs
    if not isinstance(rebound_observability, ObservabilityBundle):
        return inputs
    try:
        return replace(inputs, observability=rebound_observability)
    except (TypeError, AttributeError):
        return inputs


def _rebind_observability_logger(
    *,
    observability: object,
    manifest_id: str,
) -> object:
    """Return observability with ``manifest_id`` bound to its logger context."""
    bind_fn = getattr(observability, "bind", None)
    if callable(bind_fn):
        return bind_fn(manifest_id=manifest_id)

    logger = getattr(observability, "logger", None)
    logger_bind = getattr(logger, "bind", None)
    if not callable(logger_bind):
        return observability

    typed_observability = cast("_LoggerBindableObservability", observability)
    try:
        typed_observability.logger = logger_bind(manifest_id=manifest_id)
    except (AttributeError, TypeError):
        return observability
    return observability


__all__ = [
    "ObservabilityBundle",
    "ObservabilityContractError",
    "bind_manifest_logger_context",
]
