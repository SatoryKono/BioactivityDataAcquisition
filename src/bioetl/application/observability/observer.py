"""Pipeline Observer Context Manager.

Implements R12/R13: Observability wrapper for pipeline execution.
Handles:
- Distributed Tracing (Span creation)
- Metrics (Counter/Histogram)
- Logging (Structured logs with lifecycle context)

Unified Observability Pattern:
- All lifecycle events are emitted through this single observer
- Services use emit_event() to log structured events with metrics
- This eliminates duplicate logging across runner/preflight/postrun
"""

from __future__ import annotations

__all__ = ["LifecyclePhase", "PipelineObserver"]


import time
from contextlib import AbstractContextManager
from enum import StrEnum
from typing import TYPE_CHECKING, Any

from bioetl.application.observability.observer_context_mixin import (
    _ObserverContextManagerMixin,
)
from bioetl.application.observability.observer_event_mixin import _ObserverEventMixin
from bioetl.domain.events import PipelineEvent
from bioetl.domain.observability_contract import (
    build_observability_contract_payload as _build_observability_contract_payload,
)

if TYPE_CHECKING:
    from opentelemetry.trace import Span

    from bioetl.domain.ports import LoggerPort, MetricsPort, TracingPort
    from bioetl.domain.types import RunID, RunType

# Exposed as module attribute for compatibility with legacy patch points in tests.
build_observability_contract_payload = _build_observability_contract_payload


class LifecyclePhase(StrEnum):
    """Pipeline lifecycle phases for structured observability.

    Each phase represents a distinct stage in pipeline execution
    that should be tracked for monitoring and debugging.
    """

    STARTUP = "startup"
    PREFLIGHT = "preflight"
    LIFECYCLE_CLEAR = "lifecycle_clear"
    EXECUTION = "execution"
    POSTRUN = "postrun"
    CLEANUP = "cleanup"


class _ObserverLifecycleEmissionMixin(_ObserverEventMixin):
    """Structured lifecycle/domain event emission helpers."""

    span: Span | None
    pipeline_name: str
    _metrics: MetricsPort

    def emit_event(
        self,
        event_name: str,
        phase: LifecyclePhase,
        level: str = "info",
        **extra: Any,  # Any: structlog-compatible context kwargs
    ) -> None:
        """Emit a structured lifecycle event through unified observability.

        This is the single source of truth for lifecycle events.
        All events are logged with consistent context and optionally traced.

        Args:
            event_name: Event identifier (e.g., "preflight_started").
            phase: Current lifecycle phase.
            level: Log level ("debug", "info", "warning", "error").
            **extra: Additional context for the event.
        """
        severity = self._normalize_severity(level)
        self._emit_contract_event(
            event_name,
            severity=severity,
            phase=phase.value,
            **extra,
        )

        # Add span event if tracing is active
        if self.span:
            try:
                self.span.set_attribute(f"bioetl.{event_name}", True)
            except (AttributeError, RuntimeError, TypeError, ValueError):
                pass  # Best effort

    def emit_phase_started(
        self,
        phase: LifecyclePhase,
        **extra: Any,  # Any: structlog-compatible context kwargs
    ) -> float:
        """Emit phase start event and return start timestamp.

        Args:
            phase: Lifecycle phase starting.
            **extra: Additional context.

        Returns:
            Start timestamp for duration calculation.
        """
        self.emit_event(PipelineEvent.phase_started(phase.value), phase, **extra)
        return time.monotonic()

    def emit_phase_completed(
        self,
        phase: LifecyclePhase,
        start_time: float,
        success: bool = True,
        **extra: Any,  # Any: structlog-compatible context kwargs
    ) -> None:
        """Emit phase completion event with duration.

        Args:
            phase: Lifecycle phase completed.
            start_time: Timestamp from emit_phase_started().
            success: Whether phase completed successfully.
            **extra: Additional context.
        """
        duration = time.monotonic() - start_time
        status = "success" if success else "failed"

        self.emit_event(
            PipelineEvent.phase_completed(phase.value),
            phase,
            level="info" if success else "error",
            duration_seconds=round(duration, 4),
            status=status,
            **extra,
        )

        # Record phase duration metric
        self._metrics.observe_histogram(
            "bioetl_phase_duration_seconds",
            duration,
            labels={
                "pipeline": self.pipeline_name,
                "phase": phase.value,
                "status": status,
            },
        )

    def emit_health_check_result(
        self,
        component: str,
        healthy: bool,
        duration_ms: float | None = None,
        **extra: Any,  # Any: structlog-compatible context kwargs
    ) -> None:
        """Emit health check result for a component.

        Unified interface for health check observability.

        Args:
            component: Component name (e.g., "storage", "data_source").
            healthy: Whether component is healthy.
            duration_ms: Optional check duration in milliseconds.
            **extra: Additional context.
        """
        self.emit_event(
            PipelineEvent.HEALTH_CHECK_COMPLETED,
            LifecyclePhase.PREFLIGHT,
            level="info" if healthy else "warning",
            component=component,
            healthy=healthy,
            duration_ms=duration_ms,
            **extra,
        )

        self._metrics.set_gauge(
            "pipeline_health_check_passed",
            1.0 if healthy else 0.0,
            {"pipeline": self.pipeline_name, "component": component},
        )

    def emit_dq_anomaly(
        self,
        metric_name: str,
        severity: str,
        anomaly_type: str,
        current_value: float,
        baseline_mean: float | None = None,
        **extra: Any,  # Any: structlog-compatible context kwargs
    ) -> None:
        """Emit data quality anomaly detection event.

        Args:
            metric_name: Name of the metric with anomaly.
            severity: AnomalyRecord severity ("warning", "critical").
            anomaly_type: Type of anomaly detected.
            current_value: Current metric value.
            baseline_mean: Baseline mean for comparison.
            **extra: Additional context.
        """
        level = "error" if severity == "critical" else "warning"
        self.emit_event(
            PipelineEvent.DQ_ANOMALY_DETECTED,
            LifecyclePhase.POSTRUN,
            level=level,
            metric=metric_name,
            dq_severity=severity,
            anomaly_type=anomaly_type,
            current_value=current_value,
            baseline_mean=baseline_mean,
            **extra,
        )

        self._metrics.increment_counter(
            "dq_anomaly_detected",
            1,
            {
                "pipeline": self.pipeline_name,
                "metric": metric_name,
                "severity": severity,
                "anomaly_type": anomaly_type,
            },
        )

    def emit_vacuum_result(
        self,
        layer: str,
        table: str,
        files_removed: int,
        success: bool = True,
        **extra: Any,  # Any: structlog-compatible context kwargs
    ) -> None:
        """Emit VACUUM operation result.

        Args:
            layer: Storage layer ("silver", "gold").
            table: Table name.
            files_removed: Number of files removed.
            success: Whether operation succeeded.
            **extra: Additional context.
        """
        self.emit_event(
            PipelineEvent.VACUUM_COMPLETED,
            LifecyclePhase.POSTRUN,
            level="info" if success else "warning",
            layer=layer,
            table=table,
            files_removed=files_removed,
            success=success,
            **extra,
        )

        if success:
            self._metrics.increment_counter(
                "vacuum_files_removed_total",
                files_removed,
                {"table": table, "layer": layer},
            )

    @staticmethod
    def _derive_provider_name(pipeline_name: str) -> str:
        """Derive provider name from canonical pipeline naming."""
        if "_" not in pipeline_name:
            return pipeline_name
        provider, _entity = pipeline_name.split("_", 1)
        return provider or pipeline_name


class PipelineObserver(
    _ObserverContextManagerMixin,
    _ObserverLifecycleEmissionMixin,
    AbstractContextManager["PipelineObserver"],
):
    """Observability wrapper for pipeline execution."""

    def __init__(
        self,
        pipeline_name: str,
        run_id: RunID,
        run_type: RunType,
        metrics: MetricsPort,
        logger: LoggerPort,
        tracer: TracingPort | None = None,
    ) -> None:
        """Initialize observer."""
        self.pipeline_name = pipeline_name
        self.run_id = str(run_id)
        self.run_type = run_type.value
        self.provider_name = self._derive_provider_name(pipeline_name)
        self._metrics = metrics
        self._logger = logger
        self._tracer = tracer
        self.start_time: float | None = None
        self.span: Span | None = None
