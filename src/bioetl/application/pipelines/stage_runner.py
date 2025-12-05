"""Компонент, отвечающий за выполнение стадий пайплайна."""

from collections.abc import Callable
from datetime import datetime, timezone
import pandas as pd

from bioetl.application.pipelines.error_policy_manager import ErrorPolicyManager
from bioetl.application.pipelines.hooks_manager import HooksManager
from bioetl.domain.errors import PipelineStageError
from bioetl.domain.models import RunContext, RunResult, StageResult
from bioetl.domain.providers import ProviderId


class StageRunner:
    """Оркеструет обработку чанков и сбор результатов стадий."""

    def __init__(
        self,
        *,
        hooks_manager: HooksManager,
        error_policy_manager: ErrorPolicyManager,
        entity_name: str,
        provider_id: ProviderId,
    ) -> None:
        self._hooks_manager = hooks_manager
        self._error_policy_manager = error_policy_manager
        self._entity_name = entity_name
        self._provider_id = provider_id

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
        if not transform_started:
            self._hooks_manager.notify_stage_start("transform", context)
            transform_started = True

        df_transformed = self._error_policy_manager.execute(
            "transform",
            context,
            lambda: apply_transformers(
                transform_fn(raw_chunk),
                context,
            ),
        )
        if df_transformed is None:
            raise PipelineStageError(
                provider=self._provider_id.value,
                entity=self._entity_name,
                stage="transform",
                attempt=1,
                run_id=context.run_id,
            )

        transform_chunks += 1
        transform_count += len(df_transformed)

        if not validate_started:
            self._hooks_manager.notify_stage_start("validate", context)
            validate_started = True

        df_validated = self._error_policy_manager.execute(
            "validate", context, lambda: validate_fn(df_transformed)
        )
        if df_validated is None:
            raise PipelineStageError(
                provider=self._provider_id.value,
                entity=self._entity_name,
                stage="validate",
                attempt=1,
                run_id=context.run_id,
            )

        validate_chunks += 1
        validate_count += len(df_validated)

        if not dry_run:
            validated_chunks.append(df_validated)

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
        start_time = self._hooks_manager.get_stage_start(stage)
        duration = 0.0
        if start_time:
            duration = (
                datetime.now(timezone.utc) - start_time
            ).total_seconds()

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
        errors = self._error_policy_manager.get_last_error_messages()
        stage_result = self.make_stage_result(
            stage,
            count,
            success=False,
            errors=errors,
            chunks=chunks,
        )
        stages_results.append(stage_result)
        self._hooks_manager.notify_stage_end(stage, stage_result)
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

    @staticmethod
    def _calculate_duration(context: RunContext) -> float:
        return (
            datetime.now(timezone.utc) - context.started_at
        ).total_seconds()
