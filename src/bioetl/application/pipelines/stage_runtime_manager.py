"""Управление выполнением стадий пайплайна, хуками и политикой ошибок."""

from collections.abc import Callable, Iterable
from datetime import datetime, timezone

import pandas as pd

from bioetl.domain.enums import ErrorAction
from bioetl.domain.errors import PipelineStageError
from bioetl.domain.models import RunContext, RunResult, StageResult
from bioetl.interfaces.observability import LoggingPortABC
from bioetl.domain.pipelines.contracts import ErrorPolicyABC, PipelineHookABC
from bioetl.domain.providers import ProviderId


class StageRuntimeManagerImpl:
    """Инкапсулирует вызовы хуков, политику ошибок и исполнение стадий."""

    def __init__(
        self,
        *,
        logger: LoggingPortABC,
        provider_id: ProviderId,
        entity_name: str,
        error_policy: ErrorPolicyABC,
        default_on_skip: Callable[[str], object],
        hooks: Iterable[PipelineHookABC] | None = None,
        pipeline_id: str | None = None,
    ) -> None:
        self._logger = logger
        self._provider_id = provider_id
        self._entity_name = entity_name
        self._error_policy = error_policy
        self._default_on_skip = default_on_skip
        self._hooks: list[PipelineHookABC] = list(hooks or [])
        self._stage_starts: dict[str, datetime] = {}
        self._pipeline_id = pipeline_id
        self._current_run_id: str | None = None
        self._last_error: PipelineStageError | None = None
        self._last_stage_action: dict[str, ErrorAction | None] = {}

    @property
    def last_error(self) -> PipelineStageError | None:
        """Последняя ошибка выполнения стадии."""

        return self._last_error

    def register_hook(self, hook: PipelineHookABC) -> None:
        """Добавляет хук выполнения."""

        self._hooks.append(hook)

    def register_hooks(self, hooks: Iterable[PipelineHookABC]) -> None:
        """Добавляет список хуков выполнения."""

        for hook in hooks:
            self.register_hook(hook)

    def get_hooks(self) -> list[PipelineHookABC]:
        """Возвращает зарегистрированные хуки."""

        return self._hooks

    def reset(self) -> None:
        """Сбрасывает накопленное состояние выполнения."""

        self._stage_starts.clear()
        self._current_run_id = None
        self._last_error = None
        self._last_stage_action.clear()

    def set_logger(self, logger: LoggingPortABC) -> None:
        """Обновляет логгер для дальнейших сообщений."""

        self._logger = logger

    def set_error_policy(self, error_policy: ErrorPolicyABC) -> None:
        """Заменяет используемую политику ошибок."""

        self._error_policy = error_policy

    def notify_stage_start(self, stage: str, context: RunContext) -> None:
        """Уведомляет о старте стадии и логирует событие."""

        self._stage_starts[stage] = datetime.now(timezone.utc)
        self._current_run_id = context.run_id
        self._logger.info(
            "Stage started",
            provider=context.provider,
            entity=context.entity_name,
            run_id=context.run_id,
            stage=stage,
            pipeline=self._pipeline_id,
        )
        for hook in self._hooks:
            hook.on_stage_start(stage, context)

    def notify_stage_end(self, stage: str, result: StageResult) -> None:
        """Уведомляет о завершении стадии и логирует событие."""

        self._logger.info(
            "Stage finished",
            records=result.records_processed,
            chunks=result.chunks_processed,
            provider=self._provider_id.value,
            entity=self._entity_name,
            stage=stage,
            pipeline=self._pipeline_id,
            run_id=self._current_run_id,
            outcome="success" if result.success else "error",
        )
        for hook in self._hooks:
            hook.on_stage_end(stage, result)

    def get_stage_start(self, stage: str) -> datetime | None:
        """Возвращает время старта указанной стадии, если оно зафиксировано."""

        return self._stage_starts.get(stage)

    def execute_stage(
        self,
        stage: str,
        context: RunContext,
        action: Callable[[], object],
        *,
        attempt: int = 1,
        on_retry: Callable[[], None] | None = None,
    ) -> object:
        """Выполняет действие с учётом политики ошибок."""

        try:
            result = action()
            self._last_error = None
            self._last_stage_action[stage] = None
            return result
        except StopIteration:
            raise
        except Exception as exc:  # pylint: disable=broad-except
            error = PipelineStageError(
                provider=self._provider_id.value,
                entity=self._entity_name,
                stage=stage,
                attempt=attempt,
                run_id=context.run_id,
                cause=exc,
            )
            self._last_error = error
            self._logger.error(
                "Stage failed",
                stage=stage,
                provider=self._provider_id.value,
                entity=self._entity_name,
                run_id=context.run_id,
                error=str(exc),
            )
            for hook in self._hooks:
                hook.on_error(stage, error)

            action_on_error = self._error_policy.handle(error, context)
            self._last_stage_action[stage] = action_on_error
            if action_on_error == ErrorAction.RETRY and self._error_policy.can_retry(
                error
            ):
                if on_retry:
                    on_retry()
                return self.execute_stage(
                    stage,
                    context,
                    action,
                    attempt=attempt + 1,
                    on_retry=on_retry,
                )
            if action_on_error == ErrorAction.SKIP:
                self._logger.warning(
                    "Stage skipped due to error policy",
                    stage=stage,
                    provider=self._provider_id.value,
                    entity=self._entity_name,
                    run_id=context.run_id,
                    error=str(exc),
                )
                return self._default_on_skip(stage)

            raise error from exc

    def get_last_error_messages(self) -> list[str]:
        """Возвращает список сообщений последней ошибки."""

        if self._last_error is None:
            return []

        messages = [str(self._last_error)]
        if self._last_error.cause:
            messages.append(str(self._last_error.cause))
        return messages

    def get_last_action(self, stage: str) -> ErrorAction | None:
        """Возвращает последнее действие политики ошибок для стадии."""

        return self._last_stage_action.get(stage)

    def process_chunk(
        self,
        raw_chunk: pd.DataFrame,
        context: RunContext,
        *,
        transform_started: bool,
        transform_chunks: int,
        transform_count: int,
        validate_started: bool,
        validate_chunks: int,
        validate_count: int,
        validated_chunks: list[pd.DataFrame],
        dry_run: bool,
        transform_fn: Callable[[pd.DataFrame], pd.DataFrame],
        apply_transformers: Callable[[pd.DataFrame, RunContext], pd.DataFrame],
        validate_fn: Callable[[pd.DataFrame], pd.DataFrame],
    ) -> tuple[bool, int, int, bool, int, int]:
        """Run transform and validate stages for a single chunk."""

        (
            transform_started,
            transform_chunks,
            transform_count,
            df_transformed,
        ) = self._execute_stage(
            "transform",
            context,
            lambda: apply_transformers(transform_fn(raw_chunk), context),
            started=transform_started,
            chunks=transform_chunks,
            count=transform_count,
        )

        (
            validate_started,
            validate_chunks,
            validate_count,
            df_validated,
        ) = self._execute_stage(
            "validate",
            context,
            lambda: validate_fn(df_transformed),
            started=validate_started,
            chunks=validate_chunks,
            count=validate_count,
            dry_run=dry_run,
            validated_chunks=validated_chunks,
        )

        return (
            transform_started,
            transform_chunks,
            transform_count,
            validate_started,
            validate_chunks,
            validate_count,
        )

    def make_stage_result(
        self,
        stage: str,
        count: int,
        *,
        success: bool = True,
        errors: list[str] | None = None,
        chunks: int = 0,
    ) -> StageResult:
        """Собирает StageResult с длительностью и счётчиками."""

        start_time = self.get_stage_start(stage)
        duration = 0.0
        if start_time:
            duration = (datetime.now(timezone.utc) - start_time).total_seconds()

        return StageResult(
            stage_name=stage,
            success=success,
            records_processed=count if success else 0,
            chunks_processed=chunks if success else 0,
            duration_sec=duration,
            errors=errors or [],
        )

    def handle_stage_failure(
        self,
        stage: str,
        stages_results: list[StageResult],
        context: RunContext,
        *,
        count: int = 0,
        chunks: int = 0,
    ) -> RunResult:
        """Формирует результат неуспешного запуска и уведомляет хуки."""

        errors = self.get_last_error_messages()
        stage_result = self.make_stage_result(
            stage,
            count,
            success=False,
            errors=errors,
            chunks=chunks,
        )
        stages_results.append(stage_result)
        self.notify_stage_end(stage, stage_result)
        return RunResult(
            run_id=context.run_id,
            success=False,
            entity_name=self._entity_name,
            row_count=0,
            output_path=None,
            duration_sec=self._calculate_duration(context),
            stages=stages_results,
            errors=errors,
            meta={},
        )

    def _execute_stage(
        self,
        stage: str,
        context: RunContext,
        action: Callable[[], pd.DataFrame],
        *,
        started: bool,
        chunks: int,
        count: int,
        dry_run: bool = False,
        validated_chunks: list[pd.DataFrame] | None = None,
    ) -> tuple[bool, int, int, pd.DataFrame]:
        if not started:
            self.notify_stage_start(stage, context)
            started = True

        df_result_obj = self.execute_stage(stage, context, action)
        if df_result_obj is None:
            raise PipelineStageError(
                provider=self._provider_id.value,
                entity=self._entity_name,
                stage=stage,
                attempt=1,
                run_id=context.run_id,
            )

        if not isinstance(df_result_obj, pd.DataFrame):
            raise PipelineStageError(
                provider=self._provider_id.value,
                entity=self._entity_name,
                stage=stage,
                attempt=1,
                run_id=context.run_id,
            )
        df_result = df_result_obj

        chunks += 1
        count += len(df_result)

        if stage == "validate" and not dry_run and validated_chunks is not None:
            validated_chunks.append(df_result)

        return started, chunks, count, df_result

    @staticmethod
    def _calculate_duration(context: RunContext) -> float:
        return (datetime.now(timezone.utc) - context.started_at).total_seconds()


# Backwards compatibility for legacy imports
StageRuntimeManager = StageRuntimeManagerImpl
