"""Context manager mixin for pipeline observer lifecycle."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Self

from bioetl.application.observability.observer_event_mixin import _ObserverEventMixin
from bioetl.domain.events import PipelineEvent
from bioetl.domain.exceptions.pipeline_shutdown import PipelineShutdownError
from bioetl.domain.ports.noop import NoOpTracing

if TYPE_CHECKING:
    from types import TracebackType

    from opentelemetry.trace import Span

    from bioetl.domain.ports import MetricsPort, TracingPort


class _ObserverContextManagerMixin(_ObserverEventMixin):
    """Context-manager lifecycle orchestration for pipeline observability."""

    pipeline_name: str
    run_id: str
    run_type: str
    manifest_id: str | None
    effective_config_hash: str | None
    contract_ref: str | None
    contract_version: str | None
    composite_run_id: str | None
    start_time: float | None
    span: Span | None
    _metrics: MetricsPort
    _tracer: TracingPort | None

    def __enter__(self) -> Self:
        """Start observation (Span + Log + Metric)."""
        self.start_time = time.monotonic()
        self._start_trace_span()
        self._emit_contract_event(
            PipelineEvent.START,
            severity="info",
            run_type=self.run_type,
            phase="startup",
        )
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> bool | None:
        """End observation (Span + Log + Metric)."""
        duration = time.monotonic() - (self.start_time or 0)
        status, suppress_exception = self._resolve_status(exc_val)
        self._record_pipeline_run_metrics(duration, status)
        self._emit_pipeline_result_event(duration, status, exc_val)
        self._close_span_safely(status, duration, exc_type, exc_val, exc_tb)
        return suppress_exception

    def _start_trace_span(self) -> None:
        """Open tracing span if tracer is configured."""
        if not self._has_real_tracing():
            return
        assert self._tracer is not None
        otel_tracer = self._tracer.get_tracer("bioetl.pipeline")
        attributes = self._build_trace_attributes()
        self.span = otel_tracer.start_as_current_span(
            f"pipeline.{self.pipeline_name}",
            attributes=attributes,
        )
        self.span.__enter__()
        self._metrics.increment_counter(
            "traced_runs_total",
            1,
            labels={
                "pipeline": self.pipeline_name,
                "run_type": self.run_type,
            },
        )

    def _has_real_tracing(self) -> bool:
        """Return whether the observer uses a non-noop tracing implementation."""
        return self._tracer is not None and not isinstance(self._tracer, NoOpTracing)

    def _build_trace_attributes(self) -> dict[str, object]:
        """Build span attributes with optional correlation anchors."""
        attributes: dict[str, object] = {
            "bioetl.pipeline": self.pipeline_name,
            "bioetl.run_id": self.run_id,
            "bioetl.run_type": self.run_type,
        }
        optional_attributes = {
            "bioetl.manifest_id": self.manifest_id,
            "bioetl.effective_config_hash": self.effective_config_hash,
            "bioetl.contract_ref": self.contract_ref,
            "bioetl.contract_version": self.contract_version,
            "bioetl.composite_run_id": self.composite_run_id,
        }
        for key, value in optional_attributes.items():
            if value is None:
                continue
            attributes[key] = value
        return attributes

    @staticmethod
    def _resolve_status(exc_val: BaseException | None) -> tuple[str, bool]:
        """Resolve final pipeline status and exception suppression behavior."""
        if exc_val is None:
            return "success", False
        if isinstance(exc_val, PipelineShutdownError):
            return "shutdown", False
        return "failed", False

    def _record_pipeline_run_metrics(self, duration: float, status: str) -> None:
        """Emit pipeline duration/run metrics."""
        self._metrics.observe_histogram(
            "pipeline_duration_seconds",
            duration,
            labels={
                "pipeline": self.pipeline_name,
                "stage": "pipeline",
                "run_type": self.run_type,
                "status": status,
            },
        )
        self._metrics.increment_counter(
            "bioetl_pipeline_runs_total",
            1,
            labels={
                "pipeline": self.pipeline_name,
                "run_type": self.run_type,
                "status": status,
            },
        )

    def _emit_pipeline_result_event(
        self,
        duration: float,
        status: str,
        exc_val: BaseException | None,
    ) -> None:
        """Emit final pipeline lifecycle event."""
        log_ctx = {
            "duration_seconds": duration,
            "status": status,
            "phase": "cleanup",
        }
        if status == "failed":
            self._emit_contract_event(
                PipelineEvent.FAILED,
                severity="error",
                **log_ctx,
                error=str(exc_val),
                error_type=type(exc_val).__name__,
            )
            return
        if status == "shutdown":
            self._emit_contract_event(
                PipelineEvent.SHUTDOWN,
                severity="warning",
                **log_ctx,
                error_type="pipeline_shutdown",
            )
            return
        self._emit_contract_event(
            PipelineEvent.COMPLETE,
            severity="info",
            **log_ctx,
        )

    def _close_span_safely(
        self,
        status: str,
        duration: float,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Finalize tracing span in best-effort mode."""
        if self.span:
            try:
                self.span.set_attribute("bioetl.status", status)
                self.span.set_attribute("bioetl.duration_ms", duration * 1000)
                if status == "failed":
                    if exc_val is not None:
                        self.span.record_exception(exc_val)
                    self.span.set_attribute("error", True)
                self.span.__exit__(exc_type, exc_val, exc_tb)
                if self._tracer is not None:
                    self._tracer.flush()
            except (AttributeError, RuntimeError, TypeError, ValueError):
                pass  # Why: observer teardown is best-effort; span errors must not mask pipeline result
