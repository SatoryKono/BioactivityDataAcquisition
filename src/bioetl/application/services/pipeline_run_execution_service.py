"""Use-case service for executing prepared pipeline runners."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from bioetl.domain.exceptions import BioETLError
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
    from bioetl.domain.ports import LoggerPort, MetricsExtractorPort, RunnablePort


@dataclass(frozen=True, slots=True)
class PipelineExecutionResult:
    """Execution result normalized for PipelineRunnerService result assembly."""

    status: str
    error_message: str | None = None
    error_type: str | None = None
    metrics: JsonDict = field(default_factory=dict)
    completed_at: datetime = field(default_factory=lambda: datetime.now(tz=UTC))


class PipelineRunExecutionService:
    """Executes runnable pipelines and captures normalized outcome."""

    async def execute(
        self,
        *,
        runner: RunnablePort,
        run_logger: LoggerPort,
        metrics_extractor: MetricsExtractorPort,
    ) -> PipelineExecutionResult:
        """Execute runner and return normalized status/metrics outcome."""
        # Import inside method to avoid circular import at module import time.
        from bioetl.application.core.shutdown import PipelineShutdownError

        status = "success"
        error_message: str | None = None
        error_type: str | None = None

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
        return PipelineExecutionResult(
            status=status,
            error_message=error_message,
            error_type=error_type,
            metrics=metrics,
            completed_at=datetime.now(tz=UTC),
        )
