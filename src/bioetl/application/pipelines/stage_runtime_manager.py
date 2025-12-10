"""Управление выполнением стадий пайплайна, хуками и политикой ошибок."""

from collections.abc import Callable, Iterable
from datetime import datetime, timezone

import pandas as pd

from bioetl.application.pipelines.hook_notifier import HookNotifier
from bioetl.application.pipelines.stage_counter import StageCounter
from bioetl.application.pipelines.stage_error_handler import StageErrorHandler
from bioetl.domain.enums import ErrorAction
from bioetl.domain.errors import PipelineStageError
from bioetl.domain.models import RunContext, RunResult, StageResult
from bioetl.domain.observability import LoggingPortABC
from bioetl.domain.pipelines.contracts import ErrorPolicyABC, PipelineHookABC
from bioetl.domain.providers import ProviderId


class StageRuntimeManagerImpl:
    """
    Facade that coordinates stage execution using specialized components.

    Delegates responsibilities to:
    - HookNotifier: hook registration and event notification
    - StageCounter: record/chunk counting and stage timing
    - StageErrorHandler: error policy handling and error state
    """

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
        self._pipeline_id = pipeline_id

        self._hook_notifier = HookNotifier(
            logger=logger,
            pipeline_id=pipeline_id,
            hooks=hooks,
        )

        self._stage_counter = StageCounter()

        self._error_handler = StageErrorHandler(
            logger=logger,
            provider=provider_id.value,
            entity_name=entity_name,
            error_policy=error_policy,
            default_on_skip=default_on_skip,
        )

    @property
    def last_error(self) -> PipelineStageError | None:
        """Последняя ошибка выполнения стадии."""
        return self._error_handler.last_error

    def register_hook(self, hook: PipelineHookABC) -> None:
        """Добавляет хук выполнения."""
        self._hook_notifier.register_hook(hook)

    def register_hooks(self, hooks: Iterable[PipelineHookABC]) -> None:
        """Добавляет список хуков выполнения."""
        self._hook_notifier.register_hooks(hooks)

    def get_hooks(self) -> list[PipelineHookABC]:
        """Возвращает зарегистрированные хуки."""
        return self._hook_notifier.get_hooks()

    def reset(self) -> None:
        """Сбрасывает накопленное состояние выполнения."""
        self._hook_notifier.reset()
        self._stage_counter.reset()
        self._error_handler.reset()

    def set_logger(self, logger: LoggingPortABC) -> None:
        """Обновляет логгер для дальнейших сообщений."""
        self._logger = logger
        self._hook_notifier.set_logger(logger)
        self._error_handler.set_logger(logger)

    def set_error_policy(self, error_policy: ErrorPolicyABC) -> None:
        """Заменяет используемую политику ошибок."""
        self._error_handler.set_error_policy(error_policy)

    def notify_stage_start(self, stage: str, context: RunContext) -> None:
        """Уведомляет о старте стадии и логирует событие."""
        self._stage_counter.mark_stage_start(stage)
        self._hook_notifier.notify_stage_start(
            stage,
            context,
            provider=self._provider_id.value,
            entity_name=self._entity_name,
        )

    def notify_stage_end(self, stage: str, result: StageResult) -> None:
        """Уведомляет о завершении стадии и логирует событие."""
        self._hook_notifier.notify_stage_end(
            stage,
            result,
            provider=self._provider_id.value,
            entity_name=self._entity_name,
        )

    def get_stage_start(self, stage: str) -> datetime | None:
        """Возвращает время старта указанной стадии, если оно зафиксировано."""
        return self._stage_counter.get_stage_start(stage)

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
            self._error_handler.clear_error()
            return result
        except StopIteration:
            raise
        except Exception as exc:  # pylint: disable=broad-except
            error_action, pipeline_error = self._error_handler.handle_error(
                stage, exc, context, attempt=attempt
            )

            self._hook_notifier.notify_stage_error(stage, pipeline_error)

            if error_action == ErrorAction.RETRY and self._error_handler.should_retry(
                pipeline_error
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

            if error_action == ErrorAction.SKIP:
                self._error_handler.log_skip(stage, context, exc)
                return self._error_handler.get_skip_value(stage)

            raise pipeline_error from exc

    def get_last_error_messages(self) -> list[str]:
        """Возвращает список сообщений последней ошибки."""
        return self._error_handler.get_last_error_messages()

    def get_last_action(self, stage: str) -> ErrorAction | None:
        """Возвращает последнее действие политики ошибок для стадии."""
        return self._error_handler.get_last_action(stage)

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
        return self._stage_counter.make_stage_result(
            stage,
            success=success,
            errors=errors,
            override_count=count,
            override_chunks=chunks,
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
