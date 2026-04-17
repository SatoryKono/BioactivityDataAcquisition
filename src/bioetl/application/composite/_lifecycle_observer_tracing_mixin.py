"""Tracing and metric helpers for CompositeLifecycleObserverService."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Protocol

from bioetl.domain.observability_contract import build_observability_contract_payload

if TYPE_CHECKING:
    from types import TracebackType

    from bioetl.domain.ports import LoggerPort, MetricsPort, TracingPort


_PIPELINE_TRACE_NAMESPACE = "bioetl.pipeline"


class _CompositeSpanHandleProtocol(Protocol):
    """Minimal span handle surface used by composite lifecycle tracing."""

    def __enter__(self) -> object: ...

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> object | None: ...

    def set_attribute(self, key: str, value: object) -> None: ...

    def record_exception(self, exception: Exception) -> None: ...


class _CompositeLifecycleTracingHost(Protocol):
    """Structural contract required by composite lifecycle tracing helpers."""

    logger: LoggerPort
    metrics: MetricsPort | None
    tracer: TracingPort | None
    _run_start_times: dict[str, float]
    _phase_start_times: dict[tuple[str, str], float]
    _run_spans: dict[str, _CompositeSpanHandleProtocol]
    _phase_spans: dict[tuple[str, str], _CompositeSpanHandleProtocol]


class CompositeLifecycleTracingMixin:
    """Tracing and metric helpers for composite lifecycle publication."""

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

    def _has_real_tracing(self: _CompositeLifecycleTracingHost) -> bool:
        """Return whether a non-noop tracer is configured."""
        return (
            self.tracer is not None
            and getattr(self.tracer, "is_noop", False) is not True
        )

    def _build_run_trace_attributes(
        self: _CompositeLifecycleTracingHost,
        *,
        composite_name: str,
        run_id: str,
    ) -> dict[str, object]:
        """Build bounded trace attributes for one composite run span."""
        pipeline_name = self._pipeline_name(composite_name)
        return {
            _PIPELINE_TRACE_NAMESPACE: pipeline_name,
            "bioetl.run_id": run_id,
            "bioetl.run_type": "composite",
            "bioetl.composite": composite_name,
        }

    def _build_phase_trace_attributes(
        self: _CompositeLifecycleTracingHost,
        *,
        composite_name: str,
        run_id: str,
        phase_name: str,
    ) -> dict[str, object]:
        """Build bounded trace attributes for one composite phase span."""
        return {
            **self._build_run_trace_attributes(
                composite_name=composite_name,
                run_id=run_id,
            ),
            "bioetl.phase": phase_name,
        }

    @staticmethod
    def _filter_reserved_context(
        context: dict[str, object],
        *,
        reserved_keys: set[str] | None = None,
    ) -> dict[str, object]:
        """Drop reserved contract keys from caller-provided event context."""
        reserved = reserved_keys or {"composite", "run_id"}
        return {key: value for key, value in context.items() if key not in reserved}

    def _emit_contract_event(
        self: _CompositeLifecycleTracingHost,
        event_name: str,
        *,
        composite_name: str,
        run_id: str,
        severity: str,
        **context: object,
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
        self: _CompositeLifecycleTracingHost,
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
        self: _CompositeLifecycleTracingHost,
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

    def _start_run_span(
        self: _CompositeLifecycleTracingHost,
        *,
        composite_name: str,
        run_id: str,
    ) -> None:
        """Start one composite run span when tracing is enabled."""
        if not self._has_real_tracing():
            return
        assert self.tracer is not None
        pipeline_name = self._pipeline_name(composite_name)
        span = self.tracer.get_tracer(_PIPELINE_TRACE_NAMESPACE).start_as_current_span(
            f"pipeline.{pipeline_name}",
            attributes=self._build_run_trace_attributes(
                composite_name=composite_name,
                run_id=run_id,
            ),
        )
        span.__enter__()
        self._run_spans[run_id] = span
        if self.metrics is not None:
            self.metrics.increment_counter(
                "bioetl_traced_runs_total",
                1,
                labels={
                    "pipeline": pipeline_name,
                    "run_type": "composite",
                },
            )

    def _start_phase_span(
        self: _CompositeLifecycleTracingHost,
        *,
        composite_name: str,
        run_id: str,
        phase_name: str,
    ) -> None:
        """Start one composite phase span when tracing is enabled."""
        if not self._has_real_tracing():
            return
        assert self.tracer is not None
        span = self.tracer.get_tracer(_PIPELINE_TRACE_NAMESPACE).start_as_current_span(
            f"pipeline.{self._pipeline_name(composite_name)}.{phase_name}",
            attributes=self._build_phase_trace_attributes(
                composite_name=composite_name,
                run_id=run_id,
                phase_name=phase_name,
            ),
        )
        span.__enter__()
        self._phase_spans[(run_id, phase_name)] = span

    def _close_span_safely(
        self: _CompositeLifecycleTracingHost,
        span: _CompositeSpanHandleProtocol | None,
        *,
        status: str,
        duration_seconds: float | None,
        error: Exception | None = None,
        flush_tracer: bool = False,
    ) -> None:
        """Finalize one span in best-effort mode."""
        if span is None:
            return
        try:
            span.set_attribute("bioetl.status", status)
            if duration_seconds is not None:
                span.set_attribute("bioetl.duration_ms", duration_seconds * 1000)
            if error is not None:
                span.record_exception(error)
                span.set_attribute("error", True)
            span.__exit__(
                type(error) if error is not None else None,
                error,
                getattr(error, "__traceback__", None),
            )
            if flush_tracer and self.tracer is not None:
                self.tracer.flush()
        except (AttributeError, RuntimeError, TypeError, ValueError):
            pass

    def _close_phase_span(
        self: _CompositeLifecycleTracingHost,
        *,
        run_id: str,
        phase_name: str,
        status: str,
        duration_seconds: float | None,
        error: Exception | None = None,
    ) -> None:
        """Finalize one tracked phase span."""
        self._close_span_safely(
            self._phase_spans.pop((run_id, phase_name), None),
            status=status,
            duration_seconds=duration_seconds,
            error=error,
        )

    def _close_active_phase_spans_for_run(
        self: _CompositeLifecycleTracingHost,
        *,
        run_id: str,
        status: str,
        error: Exception | None = None,
    ) -> None:
        """Finalize any still-open phase spans for one run."""
        phase_keys = [
            phase_key for phase_key in self._phase_spans if phase_key[0] == run_id
        ]
        for _, phase_name in phase_keys:
            phase_start_time = self._phase_start_times.pop((run_id, phase_name), None)
            phase_duration = None
            if phase_start_time is not None:
                phase_duration = time.monotonic() - phase_start_time
            self._close_phase_span(
                run_id=run_id,
                phase_name=phase_name,
                status=status,
                duration_seconds=phase_duration,
                error=error,
            )

    def _close_run_span(
        self: _CompositeLifecycleTracingHost,
        *,
        run_id: str,
        status: str,
        duration_seconds: float | None,
        error: Exception | None = None,
    ) -> None:
        """Finalize the tracked composite run span."""
        self._close_span_safely(
            self._run_spans.pop(run_id, None),
            status=status,
            duration_seconds=duration_seconds,
            error=error,
            flush_tracer=True,
        )

    def _clear_run_state(self: _CompositeLifecycleTracingHost, run_id: str) -> None:
        """Drop cached monotonic timing state for one composite run."""
        self._run_start_times.pop(run_id, None)
        stale_phase_keys = [
            phase_key for phase_key in self._phase_start_times if phase_key[0] == run_id
        ]
        for phase_key in stale_phase_keys:
            self._phase_start_times.pop(phase_key, None)
            self._phase_spans.pop(phase_key, None)
        self._run_spans.pop(run_id, None)

    def _resolve_run_duration(
        self: _CompositeLifecycleTracingHost,
        run_id: str,
    ) -> float | None:
        """Return elapsed monotonic runtime if the run start was observed."""
        start_time = self._run_start_times.get(run_id)
        if start_time is None:
            return None
        return time.monotonic() - start_time
