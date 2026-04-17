"""Composite lifecycle publication service.

Owns composite runtime lifecycle publication so runner internals do not emit
PipelineEvent lifecycle records directly through LoggerPort.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from bioetl.application.composite._lifecycle_observer_tracing_mixin import (
    CompositeLifecycleTracingMixin,
    _CompositeSpanHandleProtocol,
)
from bioetl.domain.events import PipelineEvent
from bioetl.domain.ports import LoggerPort, MetricsPort, TracingPort

__all__ = ["CompositeLifecycleObserverService"]


@dataclass(slots=True)
class CompositeLifecycleObserverService(CompositeLifecycleTracingMixin):
    """Emit canonical composite lifecycle events through contract-aware seams."""

    logger: LoggerPort
    metrics: MetricsPort | None = None
    tracer: TracingPort | None = None
    _run_start_times: dict[str, float] = field(
        init=False,
        default_factory=dict,
        repr=False,
    )
    _phase_start_times: dict[tuple[str, str], float] = field(
        init=False,
        default_factory=dict,
        repr=False,
    )
    _run_spans: dict[str, _CompositeSpanHandleProtocol] = field(
        init=False,
        default_factory=dict,
        repr=False,
    )
    _phase_spans: dict[tuple[str, str], _CompositeSpanHandleProtocol] = field(
        init=False,
        default_factory=dict,
        repr=False,
    )

    def emit_run_started(self, *, composite_name: str, run_id: str) -> None:
        """Emit the canonical composite run start event."""
        self._run_start_times[run_id] = time.monotonic()
        self._start_run_span(composite_name=composite_name, run_id=run_id)
        self._emit_contract_event(
            PipelineEvent.START,
            composite_name=composite_name,
            run_id=run_id,
            severity="info",
            phase="startup",
            composite=composite_name,
            stage="composite_start",
        )

    def emit_run_failed(
        self,
        *,
        composite_name: str,
        run_id: str,
        error: Exception,
        reason_code: str,
        stage: str | None = None,
    ) -> None:
        """Emit the canonical composite run failure event."""
        log_kwargs: dict[str, object] = {
            "phase": "cleanup",
            "composite": composite_name,
            "error": str(error),
            "error_type": type(error).__name__,
            "reason_code": reason_code,
        }
        duration_seconds = self._resolve_run_duration(run_id)
        if duration_seconds is not None:
            log_kwargs["duration_seconds"] = round(duration_seconds, 4)
        if stage is not None:
            log_kwargs["stage"] = stage
        self._emit_contract_event(
            PipelineEvent.FAILED,
            composite_name=composite_name,
            run_id=run_id,
            severity="error",
            **log_kwargs,
        )
        self._record_pipeline_terminal_metrics(
            composite_name=composite_name,
            duration_seconds=duration_seconds,
            status="failed",
        )
        self._close_active_phase_spans_for_run(
            run_id=run_id,
            status="failed",
            error=error,
        )
        self._close_run_span(
            run_id=run_id,
            status="failed",
            duration_seconds=duration_seconds,
            error=error,
        )
        self._clear_run_state(run_id)

    def emit_run_shutdown(
        self,
        *,
        composite_name: str,
        run_id: str,
        error: Exception,
        reason: str,
        reason_code: str,
    ) -> None:
        """Emit the canonical composite shutdown event."""
        duration_seconds = self._resolve_run_duration(run_id)
        log_kwargs: dict[str, object] = {
            "phase": "cleanup",
            "composite": composite_name,
            "error": str(error),
            "error_type": type(error).__name__,
            "reason": reason,
            "reason_code": reason_code,
        }
        if duration_seconds is not None:
            log_kwargs["duration_seconds"] = round(duration_seconds, 4)
        self._emit_contract_event(
            PipelineEvent.SHUTDOWN,
            composite_name=composite_name,
            run_id=run_id,
            severity="warning",
            **log_kwargs,
        )
        self._record_pipeline_terminal_metrics(
            composite_name=composite_name,
            duration_seconds=duration_seconds,
            status="shutdown",
        )
        self._close_active_phase_spans_for_run(
            run_id=run_id,
            status="shutdown",
            error=error,
        )
        self._close_run_span(
            run_id=run_id,
            status="shutdown",
            duration_seconds=duration_seconds,
            error=error,
        )
        self._clear_run_state(run_id)

    def emit_phase_started(
        self,
        *,
        composite_name: str,
        run_id: str,
        phase_name: str,
        details: dict[str, object] | None = None,
    ) -> None:
        """Emit one composite phase-start lifecycle event."""
        self._phase_start_times[(run_id, phase_name)] = time.monotonic()
        self._start_phase_span(
            composite_name=composite_name,
            run_id=run_id,
            phase_name=phase_name,
        )
        log_kwargs: dict[str, object] = {
            "phase": phase_name,
            "composite": composite_name,
        }
        log_kwargs.update(
            self._filter_reserved_context(details or {}),
        )
        self._emit_contract_event(
            PipelineEvent.phase_started(phase_name),
            composite_name=composite_name,
            run_id=run_id,
            severity="info",
            **log_kwargs,
        )

    def emit_phase_completed(
        self,
        *,
        composite_name: str,
        run_id: str,
        phase_name: str,
        details: dict[str, object] | None = None,
    ) -> None:
        """Emit one composite phase-complete lifecycle event."""
        duration_seconds: float | None = None
        start_key = (run_id, phase_name)
        start_time = self._phase_start_times.pop(start_key, None)
        if start_time is not None:
            duration_seconds = time.monotonic() - start_time
        log_kwargs: dict[str, object] = {
            "phase": phase_name,
            "composite": composite_name,
            "status": "success",
        }
        if duration_seconds is not None:
            log_kwargs["duration_seconds"] = round(duration_seconds, 4)
        log_kwargs.update(
            self._filter_reserved_context(details or {}),
        )
        self._emit_contract_event(
            PipelineEvent.phase_completed(phase_name),
            composite_name=composite_name,
            run_id=run_id,
            severity="info",
            **log_kwargs,
        )
        if duration_seconds is not None:
            self._record_phase_duration(
                composite_name=composite_name,
                phase_name=phase_name,
                duration_seconds=duration_seconds,
                status="success",
            )
        self._close_phase_span(
            run_id=run_id,
            phase_name=phase_name,
            status="success",
            duration_seconds=duration_seconds,
        )

    def emit_run_completed(
        self,
        *,
        composite_name: str,
        run_id: str,
        duration_seconds: float,
        had_warnings: bool,
    ) -> None:
        """Emit the canonical composite run completion event."""
        status = "completed_with_warnings" if had_warnings else "success"
        log_kwargs: dict[str, object] = {
            "phase": "cleanup",
            "composite": composite_name,
            "duration_seconds": round(duration_seconds, 4),
            "status": status,
        }
        if had_warnings:
            log_kwargs["had_warnings"] = True
        self._emit_contract_event(
            PipelineEvent.COMPLETE,
            composite_name=composite_name,
            run_id=run_id,
            severity="info",
            **log_kwargs,
        )
        self._record_pipeline_terminal_metrics(
            composite_name=composite_name,
            duration_seconds=duration_seconds,
            status="success",
        )
        self._close_active_phase_spans_for_run(
            run_id=run_id,
            status=status,
        )
        self._close_run_span(
            run_id=run_id,
            status=status,
            duration_seconds=duration_seconds,
        )
        self._clear_run_state(run_id)
