"""Реализации хуков и политик обработки ошибок пайплайна."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, cast

from bioetl.domain.enums import ErrorAction
from bioetl.domain.errors import PipelineStageError
from bioetl.domain.models import StageResult
from bioetl.domain.pipelines.contracts import ErrorPolicyABC, PipelineHookABC
from bioetl.interfaces.observability.contracts import (
    LoggingPortABC,
    PipelineMetricsPortABC,
)


class LoggingPipelineHookImpl(PipelineHookABC):
    """Хук, логирующий события жизненного цикла стадий."""

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
    """Политика остановки пайплайна при первой ошибке."""

    def handle(self, error: PipelineStageError, context: Any) -> ErrorAction:
        """Always fail the pipeline on first error."""
        return ErrorAction.FAIL

    def can_retry(self, error: PipelineStageError) -> bool:  # noqa: ARG002 - интерфейс
        """Fail-fast policy never retries."""
        return False


class ContinueOnErrorPolicyImpl(ErrorPolicyABC):
    """Политика продолжения выполнения при ошибках стадий."""

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
    """Хук, фиксирующий метрики завершения стадий."""

    def __init__(
        self,
        *,
        pipeline_id: str,
        provider: str,
        entity_name: str,
        metrics_port: PipelineMetricsPortABC | None = None,
    ) -> None:
        self._pipeline_id = pipeline_id
        self._provider = provider
        self._entity_name = entity_name
        self._metrics = metrics_port or _create_noop_metrics_port()

    def on_stage_start(self, stage: str, context: Any) -> None:  # noqa: ARG002
        """Хук старта стадии не требует метрик."""

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
        """Метрики фиксируются в on_stage_end, поэтому обработка не требуется."""


def _create_noop_metrics_port() -> PipelineMetricsPortABC:
    """Return no-op metrics port."""

    return cast(
        PipelineMetricsPortABC,
        SimpleNamespace(
            update_stage_duration=lambda **_kwargs: None,
            update_stage_total=lambda **_kwargs: None,
        ),
    )
