"""Pipeline Observer Context Manager.

Implements R12/R13: Observability wrapper for pipeline execution.
Handles:
- Distributed Tracing (Span creation)
- Metrics (Counter/Histogram)
- Logging (Structured logs with lifecycle context)
"""

from __future__ import annotations

import time
from contextlib import AbstractContextManager
from types import TracebackType
from typing import TYPE_CHECKING, Any

from bioetl.application.core.shutdown import PipelineShutdownError
from bioetl.domain.ports import MetricsPort, TracingPort

if TYPE_CHECKING:
    import structlog

    from bioetl.domain.types import RunID, RunType


class PipelineObserver(AbstractContextManager["PipelineObserver"]):
    """Observability wrapper for pipeline execution."""

    def __init__(
        self,
        pipeline_name: str,
        run_id: RunID,
        run_type: RunType,
        metrics: MetricsPort,
        logger: structlog.BoundLogger,
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
        self.logger.info("pipeline_started", run_type=self.run_type)

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
                "pipeline_failed",
                **log_ctx,
                error=str(exc_val),
                error_type=type(exc_val).__name__,
            )
        elif status == "shutdown":
            self.logger.warning("pipeline_shutdown", **log_ctx)
        else:
            self.logger.info("pipeline_finished", **log_ctx)

        # 3. End Trace Span
        if self.span:
            self.span.set_attribute("bioetl.status", status)
            self.span.set_attribute("bioetl.duration_ms", duration * 1000)
            if status == "failed":
                self.span.record_exception(exc_val)
                self.span.set_attribute("error", True)
            self.span.__exit__(exc_type, exc_val, exc_tb)

        return suppress_exception
