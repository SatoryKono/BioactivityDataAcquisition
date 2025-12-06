"""Реализации хуков и политик обработки ошибок пайплайна."""

from __future__ import annotations

from typing import Any

from bioetl.application.pipelines.hooks import ErrorPolicyABC, PipelineHookABC
from bioetl.domain.enums import ErrorAction
from bioetl.domain.errors import PipelineStageError
from bioetl.domain.models import StageResult
from bioetl.infrastructure.logging.contracts import LoggerAdapterABC


class LoggingPipelineHookImpl(PipelineHookABC):
    """Хук, логирующий события жизненного цикла стадий."""

    def __init__(self, logger: LoggerAdapterABC) -> None:
        self._logger = logger

    def on_stage_start(self, stage: str, context: Any) -> None:
        self._logger.debug(
            "Hook: stage started",
            stage=stage,
            run_id=getattr(context, "run_id", None),
            provider=getattr(context, "provider", None),
            entity=getattr(context, "entity_name", None),
        )

    def on_stage_end(self, stage: str, result: StageResult) -> None:
        self._logger.debug(
            "Hook: stage finished",
            stage=stage,
            success=result.success,
            records=result.records_processed,
            duration_sec=result.duration_sec,
        )

    def on_error(self, stage: str, error: PipelineStageError) -> None:
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
        return ErrorAction.FAIL

    def should_retry(
        self, error: PipelineStageError
    ) -> bool:  # noqa: ARG002 - интерфейс
        return False


class ContinueOnErrorPolicyImpl(ErrorPolicyABC):
    """Политика продолжения выполнения при ошибках стадий."""

    def __init__(self, *, max_retries: int = 0) -> None:
        self._max_retries = max_retries

    def handle(self, error: PipelineStageError, context: Any) -> ErrorAction:
        if self._max_retries > 0 and error.attempt <= self._max_retries:
            return ErrorAction.RETRY
        return ErrorAction.SKIP

    def should_retry(self, error: PipelineStageError) -> bool:
        return error.attempt <= self._max_retries


__all__ = [
    "LoggingPipelineHookImpl",
    "FailFastErrorPolicyImpl",
    "ContinueOnErrorPolicyImpl",
]
