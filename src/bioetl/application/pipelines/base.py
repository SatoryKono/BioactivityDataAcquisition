"""
Базовый класс пайплайна.
"""
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable, TYPE_CHECKING
import pandas as pd

from bioetl.application.pipelines.hooks import ErrorPolicyABC, PipelineHookABC
from bioetl.domain.enums import ErrorAction
from bioetl.domain.errors import PipelineStageError
from bioetl.domain.models import RunContext, RunResult, StageResult
from bioetl.domain.providers import ProviderId
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
        self._stage_starts.clear()
        if hasattr(self._hash_service, "reset_state"):
            self._hash_service.reset_state()
        self._last_error = None

        context = RunContext(
            entity_name=self._config.entity_name,
            provider=self._provider_id.value,
            config=self._config.model_dump(),
            dry_run=dry_run,
        )

        self._enrich_context(context)
        self._logger.info("Pipeline started", run_id=context.run_id)
        stages_results: list[StageResult] = []

        extract_count = 0
        extract_chunks = 0
        transform_count = 0
        transform_chunks = 0
        validate_count = 0
        validate_chunks = 0
        write_count = 0
        write_chunks = 0
        validated_chunks: list[pd.DataFrame] = []
        transform_started = False
        validate_started = False

        try:
            self._notify_stage_start("extract", context)
            chunk_iterator: Iterable[pd.DataFrame] | None = None

            def reset_iterator() -> None:
                nonlocal chunk_iterator
                chunk_iterator = iter(self.iter_chunks(**kwargs))

            reset_iterator()
            while True:
                try:
                    raw_chunk = self._execute_with_error_policy(
                        "extract",
                        context,
                        lambda: next(chunk_iterator),
                        on_retry=reset_iterator,
                    )
                except StopIteration:
                    break

                extract_chunks += 1
                raw_chunk = raw_chunk if raw_chunk is not None else pd.DataFrame()
                extract_count += len(raw_chunk)

                (
                    transform_started,
                    transform_chunks,
                    transform_count,
                    validate_started,
                    validate_chunks,
                    validate_count,
                ) = self._process_chunk(
                    raw_chunk,
                    context,
                    transform_started,
                    transform_chunks,
                    transform_count,
                    validate_started,
                    validate_chunks,
                    validate_count,
                    validated_chunks,
                    dry_run,
                )

            if not transform_started:
                (
                    transform_started,
                    transform_chunks,
                    transform_count,
                    validate_started,
                    validate_chunks,
                    validate_count,
                ) = self._process_chunk(
                    pd.DataFrame(),
                    context,
                    transform_started,
                    transform_chunks,
                    transform_count,
                    validate_started,
                    validate_chunks,
                    validate_count,
                    validated_chunks,
                    dry_run,
                )

            stages_results.append(
                self._make_stage_result(
                    "extract",
                    extract_count,
                    chunks=extract_chunks,
                )
            )
            self._notify_stage_end("extract", stages_results[-1])

            stages_results.append(
                self._make_stage_result(
                    "transform",
                    transform_count,
                    chunks=transform_chunks,
                )
            )
            self._notify_stage_end("transform", stages_results[-1])

            stages_results.append(
                self._make_stage_result(
                    "validate",
                    validate_count,
                    chunks=validate_chunks,
                )
            )
            self._notify_stage_end("validate", stages_results[-1])

            write_result: WriteResult | None = None
            if not dry_run:
                if not self._stage_starts.get("write"):
                    self._notify_stage_start("write", context)

                df_to_write = (
                    pd.concat(validated_chunks, ignore_index=True)
                    if validated_chunks
                    else pd.DataFrame()
                )

                write_result = self._execute_with_error_policy(
                    "write",
                    context,
                    lambda: self.write(
                        df_to_write,
                        output_path,
                        context,
                    ),
                )
                if write_result is None:
                    return self._handle_stage_failure(
                        "write", stages_results, context
                    )

                write_count = write_result.row_count
                write_chunks = max(validate_chunks, 1)

                stages_results.append(
                    self._make_stage_result(
                        "write",
                        write_result.row_count,
                        chunks=write_chunks,
                    )
                )
                self._notify_stage_end("write", stages_results[-1])

            total_row_count = validate_count
            meta = (
                build_run_metadata(context, write_result)
                if write_result
                else build_dry_run_metadata(context, validate_count)
            )

            return RunResult(
                run_id=context.run_id,
                success=True,
                entity_name=self._config.entity_name,
                row_count=total_row_count,
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

    def iter_chunks(self, **kwargs: Any) -> Iterable[pd.DataFrame]:
        """Возвращает итератор по чанкам данных после extract."""
        yield self.extract(**kwargs)

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
            chunks=result.chunks_processed,
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
        chunks: int = 0,
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
            chunks_processed=chunks if success else 0,
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
        *,
        count: int = 0,
        chunks: int = 0,
    ) -> RunResult:
        errors = self._get_last_error_messages()
        stage_result = self._make_stage_result(
            stage,
            count,
            success=False,
            errors=errors,
            chunks=chunks,
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

    def _process_chunk(
        self,
        raw_chunk: pd.DataFrame,
        context: RunContext,
        transform_started: bool,
        transform_chunks: int,
        transform_count: int,
        validate_started: bool,
        validate_chunks: int,
        validate_count: int,
        validated_chunks: list[pd.DataFrame],
        dry_run: bool,
    ) -> tuple[bool, int, int, bool, int, int]:
        if not transform_started:
            self._notify_stage_start("transform", context)
            transform_started = True

        df_transformed = self._execute_with_error_policy(
            "transform",
            context,
            lambda: self._apply_transformers(
                self.transform(raw_chunk),
                context,
            ),
        )
        if df_transformed is None:
            raise PipelineStageError(
                provider=self._provider_id.value,
                entity=self._config.entity_name,
                stage="transform",
                attempt=1,
                run_id=context.run_id,
            )

        transform_chunks += 1
        transform_count += len(df_transformed)

        if not validate_started:
            self._notify_stage_start("validate", context)
            validate_started = True

        df_validated = self._execute_with_error_policy(
            "validate", context, lambda: self.validate(df_transformed)
        )
        if df_validated is None:
            raise PipelineStageError(
                provider=self._provider_id.value,
                entity=self._config.entity_name,
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

    def _run_stage(
        self,
        stage: str,
        context: RunContext,
        action: Callable[[], Any],
        *,
        attempt: int = 1,
    ) -> Any:
        self._notify_stage_start(stage, context)
        return self._execute_with_error_policy(
            stage,
            context,
            action,
            attempt=attempt,
        )

    def _execute_with_error_policy(
        self,
        stage: str,
        context: RunContext,
        action: Callable[[], Any],
        *,
        attempt: int = 1,
        on_retry: Callable[[], None] | None = None,
    ) -> Any:
        try:
            result = action()
            self._last_error = None
            return result
        except StopIteration:
            raise
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
                if on_retry:
                    on_retry()
                return self._execute_with_error_policy(
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
