"""Composite lifecycle publication service.

Owns composite runtime lifecycle publication so runner internals do not emit
PipelineEvent lifecycle records directly through LoggerPort.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import time
from typing import Any

from bioetl.domain.events import PipelineEvent
from bioetl.domain.observability_contract import build_observability_contract_payload
from bioetl.domain.ports import LoggerPort, MetricsPort

__all__ = ["CompositeLifecycleObserverService"]


@dataclass(slots=True)
class CompositeLifecycleObserverService:
    """Emit canonical composite lifecycle events through contract-aware seams."""

    logger: LoggerPort
    metrics: MetricsPort | None = None
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

    @staticmethod
    def _normalize_severity(level: str) -> str:
        """Normalize severity to the bounded contract vocabulary."""
        normalized = level.strip().lower()
        if normalized in {"debug", "info", "warning", "error"}:
            return normalized
        return "info"

    @staticmethod
    def _pipeline_name(composite_name: str) -> str:
        """Return the canonical composite pipeline name for observability."""
        return f"composite:{composite_name}"

    def _emit_contract_event(
        self,
        event_name: str,
        *,
        composite_name: str,
        run_id: str,
        severity: str,
        **context: Any,
    ) -> None:
        """Emit one lifecycle event through the canonical observability contract."""
        normalized_severity = self._normalize_severity(severity)
        payload = build_observability_contract_payload(
            event_name=event_name,
            context=context,
            default_provider="composite",
            default_pipeline=self._pipeline_name(composite_name),
            default_run_id=run_id,
            default_severity=normalized_severity,
            correlation_defaults={
                "entity": composite_name,
                "run_type": "composite",
                "composite_run_id": run_id,
            },
        )
        log_context = dict(payload.context)
        log_context.pop("event", None)
        log_method = getattr(self.logger, normalized_severity, self.logger.info)
        log_method(event_name, **log_context)
        if self.metrics is None:
            return
        self.metrics.increment_counter(
            "bioetl_observability_events_total",
            1,
            labels=payload.metric_labels,
        )

    def _record_pipeline_terminal_metrics(
        self,
        *,
        composite_name: str,
        duration_seconds: float | None,
        status: str,
    ) -> None:
        """Emit composite run duration and terminal counter metrics."""
        if self.metrics is None:
            return
        pipeline_name = self._pipeline_name(composite_name)
        if duration_seconds is not None:
            self.metrics.observe_histogram(
                "bioetl_pipeline_duration_seconds",
                duration_seconds,
                labels={
                    "pipeline": pipeline_name,
                    "stage": "pipeline",
                    "run_type": "composite",
                    "status": status,
                },
            )
        self.metrics.increment_counter(
            "bioetl_pipeline_runs_total",
            1,
            labels={
                "pipeline": pipeline_name,
                "run_type": "composite",
                "status": status,
            },
        )

    def _record_phase_duration(
        self,
        *,
        composite_name: str,
        phase_name: str,
        duration_seconds: float,
        status: str,
    ) -> None:
        """Emit composite phase duration metric."""
        if self.metrics is None:
            return
        self.metrics.observe_histogram(
            "bioetl_phase_duration_seconds",
            duration_seconds,
            labels={
                "pipeline": self._pipeline_name(composite_name),
                "phase": phase_name,
                "status": status,
            },
        )

    def _clear_run_state(self, run_id: str) -> None:
        """Drop cached monotonic timing state for one composite run."""
        self._run_start_times.pop(run_id, None)
        stale_phase_keys = [
            phase_key for phase_key in self._phase_start_times if phase_key[0] == run_id
        ]
        for phase_key in stale_phase_keys:
            self._phase_start_times.pop(phase_key, None)

    def _resolve_run_duration(self, run_id: str) -> float | None:
        """Return elapsed monotonic runtime if the run start was observed."""
        start_time = self._run_start_times.get(run_id)
        if start_time is None:
            return None
        return time.monotonic() - start_time

    def emit_run_started(self, *, composite_name: str, run_id: str) -> None:
        """Emit the canonical composite run start event."""
        self._run_start_times[run_id] = time.monotonic()
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
        log_kwargs: dict[str, object] = {
            "phase": phase_name,
            "composite": composite_name,
        }
        log_kwargs.update(details or {})
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
        log_kwargs.update(details or {})
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
        self._clear_run_state(run_id)
