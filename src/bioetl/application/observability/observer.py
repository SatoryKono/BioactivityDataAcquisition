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
from bioetl.domain.runtime_observability_publication_contract import (
    CANONICAL_DOMAIN_EVENT_EMITTER,
    CANONICAL_LIFECYCLE_EMITTER,
)
from bioetl.domain.types import HealthStatus

if TYPE_CHECKING:
    from opentelemetry.trace import Span

    from bioetl.domain.aggregates.events import DomainEvent
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


class _ObserverHealthEmissionMixin:
    """Health-check and preflight emission helpers for the pipeline observer."""

    pipeline_name: str
    _metrics: MetricsPort

    def emit_health_check_result(
        self,
        component: str,
        healthy: bool,
        duration_ms: float | None = None,
        *,
        provider: str | None = None,
        latency_ms: float | None = None,
        health_check_mode: str | None = None,
        fallback_reason: str | None = None,
        health_status: str | HealthStatus | None = None,
        **extra: Any,  # Any: structlog-compatible context kwargs
    ) -> None:
        """Emit health check result for a component."""
        resolved_status = self._resolve_health_status(
            health_status=health_status,
            healthy=healthy,
        )
        self.emit_event(
            PipelineEvent.HEALTH_CHECK_COMPLETED,
            LifecyclePhase.PREFLIGHT,
            level="info" if healthy else "warning",
            component=component,
            healthy=healthy,
            duration_ms=duration_ms,
            health_status=resolved_status.value,
            provider=provider,
            health_check_mode=health_check_mode,
            fallback_reason=fallback_reason,
            **extra,
        )

        self._metrics.set_gauge(
            "bioetl_pipeline_health_check_passed",
            1.0 if healthy else 0.0,
            {"pipeline": self.pipeline_name, "component": component},
        )
        metric_value = float(resolved_status.to_metric_value())
        self._metrics.set_gauge(
            "bioetl_health_check_status",
            metric_value,
            {"component": component},
        )
        if health_check_mode is not None:
            self._metrics.set_gauge(
                "bioetl_health_check_mode_status",
                metric_value,
                {"component": component, "mode": health_check_mode},
            )
        observed_latency_ms = latency_ms if latency_ms is not None else duration_ms
        if provider is not None and observed_latency_ms is not None:
            latency_seconds = observed_latency_ms / 1000.0
            self._metrics.observe_histogram(
                "bioetl_health_check_latency_seconds",
                latency_seconds,
                {"provider": provider},
            )
            if health_check_mode is not None:
                self._metrics.observe_histogram(
                    "bioetl_health_check_mode_latency_seconds",
                    latency_seconds,
                    {"provider": provider, "mode": health_check_mode},
                )
        if fallback_reason is not None:
            self._metrics.increment_counter(
                "bioetl_probe_mode_fallback_total",
                1,
                {
                    "pipeline": self.pipeline_name,
                    "component": component,
                    "reason": fallback_reason,
                },
            )

    def emit_health_check_summary(
        self,
        *,
        validated: bool,
        duration_seconds: float,
        overall_status: str,
        components_checked: int,
        **extra: Any,  # Any: structlog-compatible context kwargs
    ) -> None:
        """Emit summary preflight health observability through the observer contract."""
        self.emit_event(
            PipelineEvent.HEALTH_CHECK_SUMMARY_RECORDED,
            LifecyclePhase.PREFLIGHT,
            level="info" if validated else "warning",
            validated=validated,
            overall_status=overall_status,
            components_checked=components_checked,
            duration_seconds=round(duration_seconds, 4),
            **extra,
        )

        self._metrics.set_gauge(
            "bioetl_infrastructure_validated",
            1.0 if validated else 0.0,
            {"pipeline": self.pipeline_name},
        )
        self._metrics.observe_histogram(
            "bioetl_health_check_duration_seconds",
            duration_seconds,
            {"pipeline": self.pipeline_name},
        )

    @staticmethod
    def _resolve_health_status(
        *,
        health_status: str | HealthStatus | None,
        healthy: bool,
    ) -> HealthStatus:
        """Resolve explicit health statuses into the canonical enum."""
        if isinstance(health_status, HealthStatus):
            return health_status
        if isinstance(health_status, str):
            try:
                return HealthStatus(health_status.upper())
            except ValueError:
                pass
        return HealthStatus.HEALTHY if healthy else HealthStatus.UNHEALTHY


class _ObserverPostrunEmissionMixin:
    """Postrun anomaly and maintenance emission helpers."""

    pipeline_name: str
    _metrics: MetricsPort

    def emit_dq_anomaly(
        self,
        metric_name: str,
        severity: str,
        anomaly_type: str,
        current_value: float,
        baseline_mean: float | None = None,
        **extra: Any,  # Any: structlog-compatible context kwargs
    ) -> None:
        """Emit data quality anomaly detection event."""
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
            "bioetl_dq_anomaly_detected",
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
        """Emit VACUUM operation result."""
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
                "bioetl_vacuum_files_removed_total",
                files_removed,
                {"table": table, "layer": layer},
            )


class _ObserverLifecycleEmissionMixin(
    _ObserverHealthEmissionMixin,
    _ObserverPostrunEmissionMixin,
    _ObserverEventMixin,
):
    """Structured lifecycle/domain event emission helpers."""

    CANONICAL_LIFECYCLE_EMITTER = CANONICAL_LIFECYCLE_EMITTER
    CANONICAL_DOMAIN_EVENT_EMITTER = CANONICAL_DOMAIN_EVENT_EMITTER

    span: Span | None
    pipeline_name: str
    _metrics: MetricsPort

    @staticmethod
    def _resolve_domain_event_phase(
        phase_hint: str | None,
        *,
        fallback: LifecyclePhase | None,
    ) -> LifecyclePhase:
        """Resolve domain-event phase hints into canonical lifecycle phases."""
        if fallback is not None:
            return fallback
        if phase_hint is not None:
            try:
                return LifecyclePhase(phase_hint)
            except ValueError:
                pass
        return LifecyclePhase.EXECUTION

    def emit_domain_event(
        self,
        event: DomainEvent,
        *,
        phase: LifecyclePhase | None = None,
    ) -> None:
        """Emit one typed domain event through the runtime observability contract."""
        from bioetl.domain.observability_event_mapping import (
            map_domain_event_to_observability_event,
        )

        envelope = map_domain_event_to_observability_event(event)
        resolved_phase = self._resolve_domain_event_phase(
            envelope.phase_hint,
            fallback=phase,
        )
        self.emit_event(
            envelope.event_name,
            resolved_phase,
            level=envelope.severity,
            event_family=envelope.event_family,
            occurred_at=event.occurred_at.isoformat(),
            **envelope.context,
        )

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

        if success:
            self._completed_stage_count += 1

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

    @staticmethod
    def _derive_provider_name(pipeline_name: str) -> str:
        """Derive provider name from canonical pipeline naming."""
        if "_" not in pipeline_name:
            return pipeline_name
        provider, _entity = pipeline_name.split("_", 1)
        return provider or pipeline_name

    @staticmethod
    def _derive_entity_name(pipeline_name: str) -> str | None:
        """Derive entity name from canonical pipeline naming."""
        if "_" not in pipeline_name:
            return None
        _provider, entity = pipeline_name.split("_", 1)
        return entity or None


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
        manifest_id: str | None = None,
        entity: str | None = None,
        effective_config_hash: str | None = None,
        contract_ref: str | None = None,
        contract_version: str | None = None,
        composite_run_id: str | None = None,
    ) -> None:
        """Initialize observer."""
        self.pipeline_name = pipeline_name
        self.run_id = str(run_id)
        self.run_type = run_type.value
        self.provider_name = self._derive_provider_name(pipeline_name)
        self.manifest_id = manifest_id
        self.entity = entity or self._derive_entity_name(pipeline_name)
        self.effective_config_hash = effective_config_hash
        self.contract_ref = contract_ref
        self.contract_version = contract_version
        self.composite_run_id = composite_run_id
        self._metrics = metrics
        self._logger = logger
        self._tracer = tracer
        self.start_time: float | None = None
        self.span: Span | None = None
        self._completed_stage_count = 0
        self._terminal_records_processed = 0

    def capture_execution_metrics(
        self,
        metrics_snapshot: dict[str, int],
    ) -> None:
        """Capture final execution metrics for terminal domain-event emission."""
        self._terminal_records_processed = max(
            0,
            metrics_snapshot.get("records_gold", 0),
            metrics_snapshot.get("records_silver", 0),
            metrics_snapshot.get("records_bronze", 0),
            metrics_snapshot.get("records_fetched", 0),
        )
