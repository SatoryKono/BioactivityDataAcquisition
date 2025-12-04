"""
Базовый класс пайплайна.
"""
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, TYPE_CHECKING
import pandas as pd

from bioetl.core.providers import ProviderId
from bioetl.application.pipelines.hooks import ErrorPolicyABC, PipelineHookABC
from bioetl.domain.enums import ErrorAction
from bioetl.domain.errors import PipelineStageError
from bioetl.domain.models import RunContext, RunResult, StageResult
from bioetl.domain.schemas.pipeline_contracts import get_pipeline_contract
from bioetl.domain.transform.hash_service import HashService
from bioetl.domain.transform.transformers import (
    DatabaseVersionTransformer,
    FulldateTransformer,
    HashColumnsTransformer,
    IndexColumnTransformer,
    TransformerABC,
    TransformerChain,
)
from bioetl.domain.validation.service import ValidationService
from bioetl.infrastructure.config.models import PipelineConfig
from bioetl.infrastructure.logging.contracts import LoggerAdapterABC
from bioetl.infrastructure.output.contracts import WriteResult
from bioetl.infrastructure.output.metadata import (
    build_dry_run_metadata,
    build_run_metadata,
)

if TYPE_CHECKING:
    from bioetl.infrastructure.output.unified_writer import UnifiedOutputWriter


class PipelineBase(ABC):
    """
    Абстрактный базовый класс для всех ETL-пайплайнов.

    Реализует паттерн Template Method для стадий:
    extract → transform → validate → write
    """

    def __init__(
        self,
        config: PipelineConfig,
        logger: LoggerAdapterABC,
        validation_service: ValidationService,
        output_writer: "UnifiedOutputWriter",
        hash_service: HashService,
        hooks: list[PipelineHookABC] | None = None,
        error_policy: ErrorPolicyABC | None = None,
        post_transformer: TransformerABC | None = None,
    ) -> None:
        self._config = config
        self._provider_id = ProviderId(config.provider)
        self._logger = logger.bind(
            entity=config.entity_name,
            provider=self._provider_id.value,
        )
        self._validation_service = validation_service
        self._output_writer = output_writer
        self._hash_service = hash_service
        self._post_transformer = post_transformer or self._build_default_transformer()
        self._hooks: list[PipelineHookABC] = list(hooks or [])
        self._last_error: PipelineStageError | None = None
        self._stage_starts: dict[str, datetime] = {}
        self._schema_contract = get_pipeline_contract(
            config.id, default_entity=config.entity_name
        )
        from bioetl.application.pipelines.hooks_impl import (  # pylint: disable=import-outside-toplevel
            FailFastErrorPolicyImpl,
        )

        self._error_policy = error_policy or FailFastErrorPolicyImpl()

    # === Public API ===

    def run(
        self,
        output_path: Path,
        *,
        dry_run: bool = False,
        **kwargs: Any,
    ) -> RunResult:
        """
        Запускает полный цикл ETL-пайплайна.
        """
        context = RunContext(
            entity_name=self._config.entity_name,
            provider=self._provider_id.value,
            config=self._config.model_dump(),
            dry_run=dry_run,
        )

        self._enrich_context(context)
        self._logger.info("Pipeline started", run_id=context.run_id)
        stages_results: list[StageResult] = []

        try:
            df_raw = self._run_stage(
                stage="extract",
                context=context,
                action=lambda: self.extract(**kwargs),
            )
            if df_raw is None:
                return self._handle_stage_failure("extract", stages_results, context)
            stages_results.append(
                self._make_stage_result("extract", len(df_raw))
            )
            self._notify_stage_end("extract", stages_results[-1])

            df_transformed = self._run_stage(
                stage="transform",
                context=context,
                action=lambda: self._apply_transformers(
                    self.transform(df_raw),
                    context,
                ),
            )
            if df_transformed is None:
                return self._handle_stage_failure(
                    "transform", stages_results, context
                )
            stages_results.append(
                self._make_stage_result("transform", len(df_transformed))
            )
            self._notify_stage_end("transform", stages_results[-1])

            df_validated = self._run_stage(
                stage="validate",
                context=context,
                action=lambda: self.validate(df_transformed),
            )
            if df_validated is None:
                return self._handle_stage_failure("validate", stages_results, context)
            stages_results.append(
                self._make_stage_result("validate", len(df_validated))
            )
            self._notify_stage_end("validate", stages_results[-1])

            write_result: WriteResult | None = None
            if not dry_run:
                write_result = self._run_stage(
                    stage="write",
                    context=context,
                    action=lambda: self.write(
                        df_validated,
                        output_path,
                        context,
                    ),
                )
                if write_result is None:
                    return self._handle_stage_failure("write", stages_results, context)

                stages_results.append(
                    self._make_stage_result("write", write_result.row_count)
                )
                self._notify_stage_end("write", stages_results[-1])

            if write_result:
                meta = build_run_metadata(context, write_result)
            else:
                meta = build_dry_run_metadata(
                    context, len(df_validated)
                )

            return RunResult(
                run_id=context.run_id,
                success=True,
                entity_name=self._config.entity_name,
                row_count=len(df_validated),
                output_path=output_path if not dry_run else None,
                duration_sec=self._calculate_duration(context),
                stages=stages_results,
                errors=[],
                meta=meta,
            )
        except PipelineStageError as error:
            self._logger.error(
                "Pipeline failed",
                stage=error.stage,
                provider=error.provider,
                entity=error.entity,
                run_id=error.run_id,
                error=str(error.cause) if error.cause else str(error),
            )
            # Hooks are already notified in _run_stage
            raise

    # === Abstract Methods ===

    def get_database_version(self) -> str | None:
        """
        Возвращает версию базы данных источника.
        Может быть переопределено в наследниках.
        """
        return None

    @abstractmethod
    def extract(self, **kwargs: Any) -> pd.DataFrame:
        """Извлекает данные из источника."""

    @abstractmethod
    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """Преобразует сырые данные."""

    # === Concrete Methods ===

    def get_version(self) -> str:
        """Возвращает версию источника данных. По умолчанию 'unknown'."""
        return "unknown"

    def validate(self, df: pd.DataFrame) -> pd.DataFrame:
        """Валидирует DataFrame по Pandera-схеме."""
        return self._validation_service.validate(
            df=df,
            entity_name=self._schema_contract.schema_out,
        )

    def write(
        self,
        df: pd.DataFrame,
        output_path: Path,
        context: RunContext,
    ) -> WriteResult:
        """Записывает валидированный DataFrame."""
        output_schema_name = self._schema_contract.get_output_schema()
        output_columns = self._validation_service.get_schema_columns(
            output_schema_name
        )

        return self._output_writer.write_result(
            df=df,
            output_path=output_path,
            entity_name=self._config.entity_name,
            run_context=context,
            column_order=output_columns,
        )

    # === Hooks ===

    def add_hook(self, hook: PipelineHookABC) -> None:
        """Добавляет хук выполнения."""
        self._hooks.append(hook)

    def add_hooks(self, hooks: list[PipelineHookABC]) -> None:
        """Добавляет список хуков выполнения."""
        for hook in hooks:
            self.add_hook(hook)

    def set_error_policy(self, error_policy: ErrorPolicyABC) -> None:
        """Устанавливает политику обработки ошибок."""
        self._error_policy = error_policy

    def set_post_transformer(self, transformer: TransformerABC) -> None:
        """Позволяет заменить пост-обработчик трансформации."""
        self._post_transformer = transformer

    # === Internal Methods ===
    def _notify_stage_start(self, stage: str, context: RunContext) -> None:
        self._stage_starts[stage] = datetime.now(timezone.utc)
        self._logger.info(
            f"Stage started: {stage}",
            provider=context.provider,
            entity=context.entity_name,
            run_id=context.run_id,
        )
        for hook in self._hooks:
            hook.on_stage_start(stage, context)

    def _notify_stage_end(self, stage: str, result: StageResult) -> None:
        self._logger.info(
            f"Stage finished: {stage}",
            records=result.records_processed,
            provider=self._provider_id.value,
            entity=self._config.entity_name,
        )
        for hook in self._hooks:
            hook.on_stage_end(stage, result)

    def _make_stage_result(
        self,
        stage: str,
        count: int,
        *,
        success: bool = True,
        errors: list[str] | None = None,
    ) -> StageResult:
        start_time = self._stage_starts.get(stage)
        duration = 0.0
        if start_time:
            duration = (
                datetime.now(timezone.utc) - start_time
            ).total_seconds()

        return StageResult(
            stage_name=stage,
            success=success,
            records_processed=count if success else 0,
            duration_sec=duration,
            errors=errors or [],
        )

    def _calculate_duration(self, context: RunContext) -> float:
        return (
            datetime.now(timezone.utc) - context.started_at
        ).total_seconds()

    def _handle_stage_failure(
        self,
        stage: str,
        stages_results: list[StageResult],
        context: RunContext,
    ) -> RunResult:
        errors = self._get_last_error_messages()
        stage_result = self._make_stage_result(
            stage,
            0,
            success=False,
            errors=errors,
        )
        stages_results.append(stage_result)
        self._notify_stage_end(stage, stage_result)
        return RunResult(
            run_id=context.run_id,
            success=False,
            entity_name=self._config.entity_name,
            row_count=0,
            output_path=None,
            duration_sec=self._calculate_duration(context),
            stages=stages_results,
            errors=errors,
            meta={},
        )

    def _get_last_error_messages(self) -> list[str]:
        if self._last_error is None:
            return []
        messages = [str(self._last_error)]
        if self._last_error.cause:
            messages.append(str(self._last_error.cause))
        return messages

    def _build_default_transformer(self) -> TransformerABC:
        return TransformerChain(
            [
                HashColumnsTransformer(
                    hash_service=self._hash_service,
                    business_key_fields=self._config.hashing.business_key_fields,
                ),
                IndexColumnTransformer(hash_service=self._hash_service),
                DatabaseVersionTransformer(
                    hash_service=self._hash_service,
                    database_version_provider=self.get_version,
                ),
                FulldateTransformer(hash_service=self._hash_service),
            ]
        )

    def _apply_transformers(
        self, df: pd.DataFrame, context: RunContext
    ) -> pd.DataFrame:
        if not self._post_transformer:
            return df
        return self._post_transformer.apply(df, context)

    def _run_stage(
        self,
        stage: str,
        context: RunContext,
        action: Callable[[], Any],
        *,
        attempt: int = 1,
    ) -> Any:
        self._notify_stage_start(stage, context)
        try:
            result = action()
            self._last_error = None
            return result
        except Exception as exc:
            error = PipelineStageError(
                provider=self._provider_id.value,
                entity=self._config.entity_name,
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
                entity=self._config.entity_name,
                run_id=context.run_id,
                error=str(exc),
            )
            for hook in self._hooks:
                hook.on_error(stage, error)
            action_on_error = self._error_policy.handle(error, context)
            if action_on_error == ErrorAction.RETRY and self._error_policy.should_retry(
                error
            ):
                return self._run_stage(
                    stage,
                    context,
                    action,
                    attempt=attempt + 1,
                )
            if action_on_error == ErrorAction.SKIP:
                self._logger.warning(
                    "Stage skipped due to error policy",
                    stage=stage,
                    provider=self._provider_id.value,
                    entity=self._config.entity_name,
                    run_id=context.run_id,
                    error=str(exc),
                )
                return self._default_on_skip(stage)

            raise error from exc

    def _default_on_skip(self, stage: str) -> Any:
        """Возвращает безопасное значение по умолчанию при пропуске стадии."""

        import pandas as pd  # pylint: disable=import-outside-toplevel

        if stage in {"extract", "transform", "validate"}:
            return pd.DataFrame()
        return None

    def _enrich_context(self, context: RunContext) -> None:
        """
        Хук для обогащения контекста (например, добавления версии релиза).
        """
