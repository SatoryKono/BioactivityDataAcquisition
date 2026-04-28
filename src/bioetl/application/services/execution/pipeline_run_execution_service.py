"""Use-case service for executing prepared pipeline runners."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING

from bioetl.application.runtime_timestamps import (
    capture_runtime_timing_anchor,
    derive_completion_timestamp,
)
from bioetl.domain.exceptions import BioETLError
from bioetl.domain.exceptions.pipeline_shutdown import PipelineShutdownError
from bioetl.domain.types import JsonDict

__all__ = [
    "PipelineExecutionResult",
    "PipelineRunExecutionService",
]

_PIPELINE_RUN_ERRORS = (
    BioETLError,
    OSError,
    RuntimeError,
    ValueError,
    TypeError,
)


if TYPE_CHECKING:
    from bioetl.domain.ports import (
        ClockPort,
        ExecutionMetricsRunnerPort,
        LoggerPort,
        MetricsExtractorPort,
    )


@dataclass(frozen=True, slots=True)
class PipelineExecutionResult:
    """Execution result normalized for PipelineRunnerService result assembly."""

    status: str
    completed_at: datetime
    error_message: str | None = None
    error_type: str | None = None
    metrics: JsonDict = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class PipelineRunExecutionService:
    """Executes runnable pipelines and captures normalized outcome."""

    clock: ClockPort

    async def execute(
        self,
        *,
        runner: ExecutionMetricsRunnerPort,
        run_logger: LoggerPort,
        metrics_extractor: MetricsExtractorPort,
        started_at: datetime | None = None,
        started_monotonic: float | None = None,
    ) -> PipelineExecutionResult:
        """Execute runner and return normalized status/metrics outcome.

        Args:
            runner: ExecutionMetricsRunnerPort implementation containing the pipeline to run.
            run_logger: Logger port for recording completion, shutdown, or failure.
            metrics_extractor: Port for extracting pipeline metrics after execution.

        Returns:
            PipelineExecutionResult with status ('success', 'shutdown', or 'failed'),
            optional error details, extracted metrics, and completion timestamp.
        """
        status = "success"
        error_message: str | None = None
        error_type: str | None = None
        if started_at is None:
            started_at, started_monotonic = capture_runtime_timing_anchor(
                clock=self.clock,
            )
        elif started_monotonic is None:
            _, started_monotonic = capture_runtime_timing_anchor(
                clock=self.clock,
                started_at=started_at,
            )

        try:
            await runner.run()
            run_logger.info("Pipeline completed successfully")
        except PipelineShutdownError:
            status = "shutdown"
            run_logger.warning("Pipeline was gracefully shut down")
        except _PIPELINE_RUN_ERRORS as exc:
            status = "failed"
            error_message = str(exc)
            error_type = type(exc).__name__
            run_logger.exception(
                "Pipeline failed with exception",
                error_type=error_type,
            )

        metrics = metrics_extractor.extract_metrics(runner)
        completed_at, _ = derive_completion_timestamp(
            started_at=started_at,
            started_monotonic=started_monotonic,
        )
        return PipelineExecutionResult(
            status=status,
            error_message=error_message,
            error_type=error_type,
            metrics=metrics,
            completed_at=completed_at,
        )
