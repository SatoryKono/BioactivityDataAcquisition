"""Terminal lifecycle emit helpers for composite observer service."""

from __future__ import annotations

from typing import Protocol

from bioetl.domain.events import PipelineEvent
from bioetl.domain.ports import LoggerPort, MetricsPort, TracingPort

__all__ = [
    "LifecycleTerminalEmitHost",
    "emit_run_failed",
    "emit_run_shutdown",
]


class LifecycleTerminalEmitHost(Protocol):
    logger: LoggerPort
    metrics: MetricsPort | None
    tracer: TracingPort | None

    def _resolve_run_duration(self, run_id: str) -> float | None: ...

    def _emit_contract_event(
        self,
        event_name: str,
        *,
        composite_name: str,
        run_id: str,
        severity: str,
        **context: object,
    ) -> None: ...

    def _record_pipeline_terminal_metrics(
        self,
        *,
        composite_name: str,
        duration_seconds: float | None,
        status: str,
    ) -> None: ...

    def _close_active_phase_spans_for_run(
        self,
        *,
        run_id: str,
        status: str,
        error: Exception | None = None,
    ) -> None: ...

    def _close_run_span(
        self,
        *,
        run_id: str,
        status: str,
        duration_seconds: float | None,
        error: Exception | None = None,
    ) -> None: ...

    def _clear_run_state(self, run_id: str) -> None: ...


def emit_run_failed(
    host: LifecycleTerminalEmitHost,
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
    duration_seconds = host._resolve_run_duration(run_id)
    if duration_seconds is not None:
        log_kwargs["duration_seconds"] = round(duration_seconds, 4)
    if stage is not None:
        log_kwargs["stage"] = stage
    host._emit_contract_event(
        PipelineEvent.FAILED,
        composite_name=composite_name,
        run_id=run_id,
        severity="error",
        **log_kwargs,
    )
    host._record_pipeline_terminal_metrics(
        composite_name=composite_name,
        duration_seconds=duration_seconds,
        status="failed",
    )
    host._close_active_phase_spans_for_run(
        run_id=run_id,
        status="failed",
        error=error,
    )
    host._close_run_span(
        run_id=run_id,
        status="failed",
        duration_seconds=duration_seconds,
        error=error,
    )
    host._clear_run_state(run_id)


def emit_run_shutdown(
    host: LifecycleTerminalEmitHost,
    *,
    composite_name: str,
    run_id: str,
    error: Exception,
    reason: str,
    reason_code: str,
) -> None:
    """Emit the canonical composite shutdown event."""
    duration_seconds = host._resolve_run_duration(run_id)
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
    host._emit_contract_event(
        PipelineEvent.SHUTDOWN,
        composite_name=composite_name,
        run_id=run_id,
        severity="warning",
        **log_kwargs,
    )
    host._record_pipeline_terminal_metrics(
        composite_name=composite_name,
        duration_seconds=duration_seconds,
        status="shutdown",
    )
    host._close_active_phase_spans_for_run(
        run_id=run_id,
        status="shutdown",
        error=error,
    )
    host._close_run_span(
        run_id=run_id,
        status="shutdown",
        duration_seconds=duration_seconds,
        error=error,
    )
    host._clear_run_state(run_id)
