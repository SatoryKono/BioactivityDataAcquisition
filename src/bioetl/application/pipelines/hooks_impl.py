"""Pipeline hook and error policy implementations."""

from __future__ import annotations

from typing import Any

from bioetl.application.factories.noop import create_noop_metrics_port
from bioetl.domain.enums import ErrorAction
from bioetl.domain.errors import PipelineStageError
from bioetl.domain.models import StageResult
from bioetl.domain.observability import LoggingPortABC, MetricsPortABC
from bioetl.domain.pipelines.contracts import ErrorPolicyABC, PipelineHookABC


class LoggingPipelineHookImpl(PipelineHookABC):
    """Hook that logs stage lifecycle events."""

    def __init__(self, logger: LoggingPortABC) -> None:
        self._logger = logger

    def on_stage_start(self, stage: str, context: Any) -> None:
        """Log start of a pipeline stage."""
        self._logger.debug(
            "Hook: stage started",
            stage=stage,
            run_id=getattr(context, "run_id", None),
            provider=getattr(context, "provider", None),
            entity=getattr(context, "entity_name", None),
        )

    def on_stage_end(self, stage: str, result: StageResult) -> None:
        """Log completion of a pipeline stage."""
        self._logger.debug(
            "Hook: stage finished",
            stage=stage,
            success=result.success,
            records=result.records_processed,
            duration_sec=result.duration_sec,
        )

    def on_error(self, stage: str, error: PipelineStageError) -> None:
        """Log pipeline stage error details."""
        self._logger.error(
            "Hook: stage error",
            stage=stage,
            attempt=error.attempt,
            run_id=error.run_id,
            provider=error.provider,
            entity=error.entity,
            error=str(error.cause) if error.cause else str(error),
        )


class FailFastErrorPolicyImpl(ErrorPolicyABC):
    """Policy to stop pipeline on first error."""

    def handle(self, error: PipelineStageError, context: Any) -> ErrorAction:
        """Always fail the pipeline on first error."""
        return ErrorAction.FAIL

    def can_retry(self, error: PipelineStageError) -> bool:  # noqa: ARG002 - interface
        """Fail-fast policy never retries."""
        return False


class ContinueOnErrorPolicyImpl(ErrorPolicyABC):
    """Policy to continue execution on stage errors."""

    def __init__(self, *, max_retries: int = 0) -> None:
        self._max_retries = max_retries

    def handle(self, error: PipelineStageError, context: Any) -> ErrorAction:
        """Return retry or skip action based on attempts."""
        if self._max_retries > 0 and error.attempt <= self._max_retries:
            return ErrorAction.RETRY
        return ErrorAction.SKIP

    def can_retry(self, error: PipelineStageError) -> bool:
        """Determine whether another retry is allowed."""
        return error.attempt <= self._max_retries


__all__ = [
    "LoggingPipelineHookImpl",
    "MetricsPipelineHookImpl",
    "FailFastErrorPolicyImpl",
    "ContinueOnErrorPolicyImpl",
]


class MetricsPipelineHookImpl(PipelineHookABC):
    """Hook that records stage completion metrics."""

    def __init__(
        self,
        *,
        pipeline_id: str,
        provider: str,
        entity_name: str,
        metrics_port: MetricsPortABC | None = None,
    ) -> None:
        self._pipeline_id = pipeline_id
        self._provider = provider
        self._entity_name = entity_name
        self._metrics = metrics_port or create_noop_metrics_port()

    def on_stage_start(self, stage: str, context: Any) -> None:  # noqa: ARG002
        """Stage start hook does not require metrics."""

    def on_stage_end(self, stage: str, result: StageResult) -> None:
        """Record Prometheus metrics for stage completion."""
        outcome = "success" if result.success else "error"
        self._metrics.update_stage_duration(
            pipeline=self._pipeline_id,
            provider=self._provider,
            entity=self._entity_name,
            stage=stage,
            outcome=outcome,
            duration_sec=result.duration_sec,
        )
        self._metrics.update_stage_total(
            pipeline=self._pipeline_id,
            provider=self._provider,
            entity=self._entity_name,
            stage=stage,
            outcome=outcome,
        )

    def on_error(self, stage: str, error: PipelineStageError) -> None:  # noqa: ARG002
        """Metrics are recorded in on_stage_end, so no processing needed."""
