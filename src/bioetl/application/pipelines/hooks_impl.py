"""Реализации хуков и политик ошибок для пайплайна."""
from __future__ import annotations

from typing import Any

from bioetl.application.pipelines.hooks import ErrorPolicyABC, PipelineHookABC
from bioetl.domain.enums import ErrorAction
from bioetl.domain.errors import PipelineStageError
from bioetl.domain.models import StageResult
from bioetl.infrastructure.logging.contracts import LoggerAdapterABC


class LoggingPipelineHook(PipelineHookABC):
    """Хук, логирующий события стадий пайплайна."""

    def __init__(self, logger: LoggerAdapterABC) -> None:
        self._logger = logger

    def on_stage_start(self, stage: str, context: Any) -> None:
        self._logger.debug(
            "Hook: stage start",
            stage=stage,
            run_id=context.run_id,
            provider=context.provider,
            entity=context.entity_name,
        )

    def on_stage_end(self, stage: str, result: StageResult) -> None:
        self._logger.debug(
            "Hook: stage end",
            stage=stage,
            success=result.success,
            records=result.records_processed,
            duration_sec=result.duration_sec,
        )

    def on_error(self, stage: str, error: PipelineStageError) -> None:
        self._logger.error(
            "Hook: stage error",
            stage=stage,
            run_id=error.run_id,
            provider=error.provider,
            entity=error.entity,
            attempt=error.attempt,
            error=str(error.cause) if error.cause else str(error),
        )


class StopOnErrorPolicyImpl(ErrorPolicyABC):
    """Политика: останавливать пайплайн при первой ошибке."""

    def handle(self, error: PipelineStageError, context: Any) -> ErrorAction:
        return ErrorAction.FAIL

    def should_retry(self, error: PipelineStageError) -> bool:  # noqa: ARG002 - интерфейс
        return False


class ContinueOnErrorPolicyImpl(ErrorPolicyABC):
    """Политика: пропускать упавшую стадию и продолжать."""

    def handle(self, error: PipelineStageError, context: Any) -> ErrorAction:
        return ErrorAction.SKIP

    def should_retry(self, error: PipelineStageError) -> bool:  # noqa: ARG002 - интерфейс
        return False


__all__ = [
    "LoggingPipelineHook",
    "StopOnErrorPolicyImpl",
    "ContinueOnErrorPolicyImpl",
]
