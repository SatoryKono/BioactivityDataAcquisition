# Host attrs/methods provided by concrete composition (PD2 W1).
# basedpyright residual burn-down (shrink-only product surface).
"""Context manager mixin for pipeline observer lifecycle."""

from __future__ import annotations

import time
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any, Self
from uuid import UUID

from bioetl.application.observability.observer_contract import LifecyclePhase
from bioetl.application.runtime_timestamps import capture_runtime_timing_anchor
from bioetl.domain.aggregates.events import (
    PipelineCompleted,
    PipelineFailed,
    PipelineShutdown,
)
from bioetl.domain.events import PipelineEvent
from bioetl.domain.exceptions.pipeline_shutdown import PipelineShutdownError
from bioetl.domain.types import RunID

if TYPE_CHECKING:
    from types import TracebackType

    from bioetl.domain.ports import ClockPort, MetricsPort, TracingPort
    from bioetl.domain.ports.observability.tracing import SpanHandle as Span


if TYPE_CHECKING:

    class _ObserverEventMixinBase:
        """Typing-only stand-in for skipped observer event mixin imports."""

        def _emit_contract_event(
            self,
            event_name: str,
            *,
            severity: str,
            **context: Any,  # Any: event payload keys vary across lifecycle/domain emissions
        ) -> None: ...

        def emit_domain_event(
            self, event: object, *, phase: object | None = None
        ) -> None: ...

else:
    from bioetl.application.observability.observer_event_mixin import (
        _ObserverEventMixin as _ObserverEventMixinBase,
    )


class _ObserverContextManagerMixin(_ObserverEventMixinBase):
    """Context-manager lifecycle orchestration for pipeline observability."""

    pipeline_name: str  # pyright: ignore[reportUninitializedInstanceVariable]
    provider_name: str  # pyright: ignore[reportUninitializedInstanceVariable]
    run_id: str  # pyright: ignore[reportUninitializedInstanceVariable]
    run_type: str  # pyright: ignore[reportUninitializedInstanceVariable]
    manifest_id: str | None  # pyright: ignore[reportUninitializedInstanceVariable]
    effective_config_hash: str | None  # pyright: ignore[reportUninitializedInstanceVariable]
    contract_ref: str | None  # pyright: ignore[reportUninitializedInstanceVariable]
    contract_version: str | None  # pyright: ignore[reportUninitializedInstanceVariable]
    composite_run_id: str | None  # pyright: ignore[reportUninitializedInstanceVariable]
    start_time: float | None  # pyright: ignore[reportUninitializedInstanceVariable]
    wall_start_time: datetime | None  # pyright: ignore[reportUninitializedInstanceVariable]
    span: Span | None  # pyright: ignore[reportUninitializedInstanceVariable]
    _completed_stage_count: int  # pyright: ignore[reportUninitializedInstanceVariable]
    _terminal_records_processed: int  # pyright: ignore[reportUninitializedInstanceVariable]
    _metrics: MetricsPort  # pyright: ignore[reportUninitializedInstanceVariable]
    _tracer: TracingPort | None  # pyright: ignore[reportUninitializedInstanceVariable]
    _clock: ClockPort  # pyright: ignore[reportUninitializedInstanceVariable]

    def _domain_run_id(self) -> RunID:
        """Coerce the observer's string run id into the domain RunID type."""
        return RunID(UUID(self.run_id))

    def __enter__(self) -> Self:
        """Start observation (Span + Log + Metric)."""
        wall_start_time, started_monotonic = capture_runtime_timing_anchor(
            clock=self._clock,
        )
        self.wall_start_time = wall_start_time
        self.start_time = started_monotonic
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
        self.span.__enter__()  # pyright: ignore[reportOptionalMemberAccess]
        self._metrics.increment_counter(
            "bioetl_traced_runs_total",
            1,
            labels={
                "pipeline": self.pipeline_name,
                "run_type": self.run_type,
            },
        )

    def _has_real_tracing(self) -> bool:
        """Return whether the observer uses a non-noop tracing implementation."""
        return (
            self._tracer is not None
            and getattr(self._tracer, "is_noop", False) is not True
        )

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
            "bioetl_pipeline_duration_seconds",
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
        # Pipeline terminal outcomes must not contaminate provider health-check
        # counters (OBS-MET-004 / #6729). Health probes own that family only.

    def _emit_pipeline_result_event(
        self,
        duration: float,
        status: str,
        exc_val: BaseException | None,
    ) -> None:
        """Emit final pipeline lifecycle event."""
        if status == "failed":
            self.emit_domain_event(
                PipelineFailed(
                    occurred_at=self._build_pipeline_result_timestamp(
                        self.wall_start_time,
                        duration,
                    ),
                    run_id=self._domain_run_id(),
                    pipeline_name=self.pipeline_name,
                    failed_stage="unknown",
                    error=str(exc_val),
                    error_type=type(exc_val).__name__,
                ),
                phase=LifecyclePhase.CLEANUP,
            )
            return
        if status == "shutdown":
            self.emit_domain_event(
                PipelineShutdown(
                    occurred_at=self._build_pipeline_result_timestamp(
                        self.wall_start_time,
                        duration,
                    ),
                    run_id=self._domain_run_id(),
                    pipeline_name=self.pipeline_name,
                    records_processed=self._terminal_records_processed,
                ),
                phase=LifecyclePhase.CLEANUP,
            )
            return
        self.emit_domain_event(
            PipelineCompleted(
                occurred_at=self._build_pipeline_result_timestamp(
                    self.wall_start_time,
                    duration,
                ),
                run_id=self._domain_run_id(),
                pipeline_name=self.pipeline_name,
                records_processed=self._terminal_records_processed,
                duration_seconds=duration,
                stages_count=self._completed_stage_count,
            ),
            phase=LifecyclePhase.CLEANUP,
        )

    @staticmethod
    def _build_pipeline_result_timestamp(
        wall_start_time: datetime | None,
        duration_seconds: float,
    ) -> datetime:
        """Return deterministic terminal event timestamp from the captured start."""
        if wall_start_time is None:
            raise RuntimeError(
                "PipelineObserver terminal event timestamp requires wall_start_time. "
                "The observer context manager must capture startup time before teardown."
            )
        return wall_start_time + timedelta(seconds=duration_seconds)

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
