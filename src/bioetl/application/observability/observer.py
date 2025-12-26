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

import time
from contextlib import AbstractContextManager
from enum import Enum
from typing import TYPE_CHECKING, Any

from bioetl.application.core.shutdown import PipelineShutdownError
from bioetl.domain.events import PipelineEvent

if TYPE_CHECKING:
    from types import TracebackType

    from bioetl.domain.ports import LoggerPort, MetricsPort, TracingPort
    from bioetl.domain.types import RunID, RunType


class LifecyclePhase(str, Enum):
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


class PipelineObserver(AbstractContextManager["PipelineObserver"]):
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
        self.metrics = metrics
        self.logger = logger
        self.tracer = tracer

        self.start_time: float | None = None
        self.span: Any = None

    def __enter__(self) -> PipelineObserver:
        """Start observation (Span + Log + Metric)."""
        self.start_time = time.monotonic()

        # 1. Start Trace Span
        if self.tracer:
            otel_tracer = self.tracer.get_tracer("bioetl.pipeline")
            self.span = otel_tracer.start_as_current_span(
                f"pipeline.{self.pipeline_name}",
                attributes={
                    "bioetl.pipeline": self.pipeline_name,
                    "bioetl.run_id": self.run_id,
                    "bioetl.run_type": self.run_type,
                },
            )
            self.span.__enter__()

        # 2. Log Start
        self.logger.info(PipelineEvent.START, run_type=self.run_type)

        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> bool | None:
        """End observation (Span + Log + Metric)."""
        duration = time.monotonic() - (self.start_time or 0)
        status = "success"
        suppress_exception = False

        if exc_val:
            if isinstance(exc_val, PipelineShutdownError):
                status = "shutdown"
                suppress_exception = (
                    True  # We suppress the shutdown signal to allow clean exit
                )
            else:
                status = "failed"

        # 1. Metrics (Histogram)
        self.metrics.observe_histogram(
            "bioetl_pipeline_duration_seconds",
            duration,
            labels={
                "pipeline": self.pipeline_name,
                "run_type": self.run_type,
                "status": status,
            },
        )
        self.metrics.increment_counter(
            "bioetl_pipeline_runs_total",
            1,
            labels={
                "pipeline": self.pipeline_name,
                "run_type": self.run_type,
                "status": status,
            },
        )

        # 2. Log Result
        log_ctx = {
            "duration_seconds": duration,
            "status": status,
        }
        if status == "failed":
            self.logger.error(
                PipelineEvent.ERROR,
                **log_ctx,
                error=str(exc_val),
                error_type=type(exc_val).__name__,
            )
        elif status == "shutdown":
            self.logger.warning(PipelineEvent.SHUTDOWN, **log_ctx)
        else:
            self.logger.info(PipelineEvent.COMPLETE, **log_ctx)

        # 3. End Trace Span (O3: handle close errors gracefully)
        if self.span:
            try:
                self.span.set_attribute("bioetl.status", status)
                self.span.set_attribute("bioetl.duration_ms", duration * 1000)
                if status == "failed":
                    self.span.record_exception(exc_val)
                    self.span.set_attribute("error", True)
                self.span.__exit__(exc_type, exc_val, exc_tb)
            except Exception:
                # Best effort - don't fail the pipeline on tracing cleanup
                pass

        return suppress_exception

    # --- Unified Lifecycle Event Emission ---

    def emit_event(
        self,
        event_name: str,
        phase: LifecyclePhase,
        level: str = "info",
        **extra: Any,
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
        ctx = {
            "phase": phase.value,
            "pipeline": self.pipeline_name,
            "run_id": self.run_id,
            **extra,
        }

        log_method = getattr(self.logger, level, self.logger.info)
        log_method(event_name, **ctx)

        # Add span event if tracing is active
        if self.span:
            try:
                self.span.set_attribute(f"bioetl.{event_name}", True)
            except Exception:
                pass  # Best effort

    def emit_phase_started(
        self,
        phase: LifecyclePhase,
        **extra: Any,
    ) -> float:
        """Emit phase start event and return start timestamp.

        Args:
            phase: Lifecycle phase starting.
            **extra: Additional context.

        Returns:
            Start timestamp for duration calculation.
        """
        self.emit_event(f"{phase.value}_started", phase, **extra)
        return time.monotonic()

    def emit_phase_completed(
        self,
        phase: LifecyclePhase,
        start_time: float,
        success: bool = True,
        **extra: Any,
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
            f"{phase.value}_completed",
            phase,
            level="info" if success else "error",
            duration_seconds=round(duration, 4),
            status=status,
            **extra,
        )

        # Record phase duration metric
        self.metrics.observe_histogram(
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
        **extra: Any,
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
            "health_check_completed",
            LifecyclePhase.PREFLIGHT,
            level="info" if healthy else "warning",
            component=component,
            healthy=healthy,
            duration_ms=duration_ms,
            **extra,
        )

        self.metrics.set_gauge(
            PipelineEvent.HEALTH_CHECK_PASSED,
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
        **extra: Any,
    ) -> None:
        """Emit data quality anomaly detection event.

        Args:
            metric_name: Name of the metric with anomaly.
            severity: Anomaly severity ("warning", "critical").
            anomaly_type: Type of anomaly detected.
            current_value: Current metric value.
            baseline_mean: Baseline mean for comparison.
            **extra: Additional context.
        """
        level = "error" if severity == "critical" else "warning"
        self.emit_event(
            "dq_anomaly_detected",
            LifecyclePhase.POSTRUN,
            level=level,
            metric=metric_name,
            severity=severity,
            anomaly_type=anomaly_type,
            current_value=current_value,
            baseline_mean=baseline_mean,
            **extra,
        )

        self.metrics.increment_counter(
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
        **extra: Any,
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
            "vacuum_completed",
            LifecyclePhase.POSTRUN,
            level="info" if success else "warning",
            layer=layer,
            table=table,
            files_removed=files_removed,
            success=success,
            **extra,
        )

        if success:
            self.metrics.increment_counter(
                "vacuum_files_removed",
                files_removed,
                {"pipeline": self.pipeline_name, "layer": layer},
            )
