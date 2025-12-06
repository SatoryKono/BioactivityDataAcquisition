"""
Базовый класс пайплайна.
"""

from abc import ABC
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Iterable

import pandas as pd

from bioetl.application.config.pipeline_config_schema import PipelineConfig
from bioetl.application.pipelines.contracts import ExtractorABC
from bioetl.application.pipelines.error_policy_manager import ErrorPolicyManager
from bioetl.application.pipelines.hooks_manager import HooksManager
from bioetl.application.pipelines.stage_runner import StageRunner
from bioetl.domain.enums import ErrorAction
from bioetl.domain.errors import PipelineStageError
from bioetl.domain.models import RunContext, RunResult, StageResult
from bioetl.domain.pipelines.contracts import ErrorPolicyABC, PipelineHookABC
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
from bioetl.infrastructure.logging.contracts import LoggerAdapterABC
from bioetl.infrastructure.observability import metrics
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

    Использует композицию для стадий (Extractor, Transformer).
    """

    def __init__(
        self,
        config: PipelineConfig,
        logger: LoggerAdapterABC,
        validation_service: ValidationService,
        output_writer: "UnifiedOutputWriter",
        hash_service: HashService,
        extractor: ExtractorABC | None = None,
        hooks: list[PipelineHookABC] | None = None,
        error_policy: ErrorPolicyABC | None = None,
        transformer: TransformerABC | None = None,
        post_transformer: TransformerABC | None = None,
    ) -> None:
        self._config = config
        self._provider_id = ProviderId(config.provider)
        self._logger = logger.bind(
            entity=config.entity_name,
            provider=self._provider_id.value,
            pipeline=config.id,
        )
        self._validation_service = validation_service
        self._output_writer = output_writer
        self._hash_service = hash_service
        self._extractor = extractor
        self._transformer = transformer
        self._post_transformer = post_transformer or self._build_default_transformer()
        self._schema_contract = get_pipeline_contract(
            config.id, default_entity=config.entity_name
        )
        from bioetl.application.pipelines.hooks_impl import (  # pylint: disable=import-outside-toplevel
            FailFastErrorPolicyImpl,
        )

        self._hooks_manager = HooksManager(
            logger=self._logger,
            provider_id=self._provider_id,
            entity_name=self._config.entity_name,
            hooks=hooks,
            pipeline_id=self._config.id,
        )
        self._error_policy = error_policy or FailFastErrorPolicyImpl()
        self._error_policy_manager = ErrorPolicyManager(
            error_policy=self._error_policy,
            hooks_manager=self._hooks_manager,
            logger=self._logger,
            provider_id=self._provider_id,
            entity_name=self._config.entity_name,
            default_on_skip=self._default_on_skip,
        )
        self._stage_runner = StageRunner(
            hooks_manager=self._hooks_manager,
            error_policy_manager=self._error_policy_manager,
            entity_name=self._config.entity_name,
            provider_id=self._provider_id,
        )
        self._instrument_extract_calls()

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
        self._hooks_manager.reset()
        self._error_policy_manager.reset()
        if hasattr(self._hash_service, "reset_state"):
            self._hash_service.reset_state()

        context = self._build_context(dry_run)
        self._logger = self._logger.bind(run_id=context.run_id)
        self._hooks_manager.set_logger(self._logger)
        self._error_policy_manager.set_logger(self._logger)
        self._logger.info("Pipeline started", run_id=context.run_id)
        stages_results: list[StageResult] = []
        counters = self._init_stage_counters()
        validated_chunks: list[pd.DataFrame] = []

        try:
            self._hooks_manager.notify_stage_start("extract", context)
            counters, validated_chunks = self._process_extract_stage(
                context, counters, validated_chunks, dry_run, kwargs
            )

            self._append_stage_result(
                stages_results,
                "extract",
                counters["extract_count"],
                counters["extract_chunks"],
            )
            self._record_stage_metrics(stages_results[-1], "extract")

            self._append_stage_result(
                stages_results,
                "transform",
                counters["transform_count"],
                counters["transform_chunks"],
            )
            self._record_stage_metrics(stages_results[-1], "transform")

            self._append_stage_result(
                stages_results,
                "validate",
                counters["validate_count"],
                counters["validate_chunks"],
            )
            self._record_stage_metrics(stages_results[-1], "validate")

            write_result: WriteResult | None = None
            if not dry_run:
                write_result, counters = self._perform_write_stage(
                    context, validated_chunks, output_path, counters, stages_results
                )
                if write_result is None:
                    run_result = self._stage_runner.handle_stage_failure(
                        "write", stages_results, context
                    )
                    if run_result.stages:
                        self._record_stage_metrics(run_result.stages[-1], "write")
                    return run_result

                self._record_stage_metrics(stages_results[-1], "write")

            meta = (
                build_run_metadata(context, write_result)
                if write_result
                else build_dry_run_metadata(context, counters["validate_count"])
            )

            return RunResult(
                run_id=context.run_id,
                success=True,
                entity_name=self._config.entity_name,
                row_count=counters["validate_count"],
                output_path=output_path if not dry_run else None,
                duration_sec=self._calculate_duration(context),
                stages=stages_results,
                errors=[],
                meta=meta,
            )
        except PipelineStageError as error:
            stage_result = self._stage_runner.make_stage_result(
                error.stage,
                0,
                success=False,
                errors=self._error_policy_manager.get_last_error_messages(),
            )
            stages_results.append(stage_result)
            self._hooks_manager.notify_stage_end(error.stage, stage_result)
            self._record_stage_metrics(stage_result, error.stage)
            self._logger.error(
                "Pipeline failed",
                stage=error.stage,
                provider=error.provider,
                entity=error.entity,
                run_id=error.run_id,
                error=str(error.cause) if error.cause else str(error),
            )
            raise

    def _build_context(self, dry_run: bool) -> RunContext:
        context = RunContext(
            entity_name=self._config.entity_name,
            provider=self._provider_id.value,
            config=self._config.model_dump(),
            dry_run=dry_run,
        )
        self._enrich_context(context)
        return context

    def _init_stage_counters(self) -> dict[str, int]:
        return {
            "extract_count": 0,
            "extract_chunks": 0,
            "transform_count": 0,
            "transform_chunks": 0,
            "validate_count": 0,
            "validate_chunks": 0,
            "write_count": 0,
            "write_chunks": 0,
        }

    def _process_extract_stage(
        self,
        context: RunContext,
        counters: dict[str, int],
        validated_chunks: list[pd.DataFrame],
        dry_run: bool,
        kwargs: dict[str, Any],
    ) -> tuple[dict[str, int], list[pd.DataFrame]]:
        chunk_iterator: Iterable[pd.DataFrame] | None = None
        transform_started = False
        validate_started = False

        def reset_iterator() -> None:
            nonlocal chunk_iterator
            chunk_iterator = self._create_chunk_iterator(context, **kwargs)

        reset_iterator()
        while True:
            try:
                raw_chunk = self._error_policy_manager.execute(
                    "extract",
                    context,
                    lambda: next(chunk_iterator),  # type: ignore
                    on_retry=reset_iterator,
                )
            except StopIteration:
                break

            counters["extract_chunks"] += 1
            raw_chunk = raw_chunk if raw_chunk is not None else pd.DataFrame()
            counters["extract_count"] += len(raw_chunk)

            (
                transform_started,
                counters["transform_chunks"],
                counters["transform_count"],
                validate_started,
                counters["validate_chunks"],
                counters["validate_count"],
            ) = self._stage_runner.process_chunk(
                raw_chunk,
                context,
                transform_started=transform_started,
                transform_chunks=counters["transform_chunks"],
                transform_count=counters["transform_count"],
                validate_started=validate_started,
                validate_chunks=counters["validate_chunks"],
                validate_count=counters["validate_count"],
                validated_chunks=validated_chunks,
                dry_run=dry_run,
                transform_fn=self.transform,
                apply_transformers=self._apply_transformers,
                validate_fn=self.validate,
            )

        if not transform_started:
            (
                transform_started,
                counters["transform_chunks"],
                counters["transform_count"],
                validate_started,
                counters["validate_chunks"],
                counters["validate_count"],
            ) = self._stage_runner.process_chunk(
                pd.DataFrame(),
                context,
                transform_started=transform_started,
                transform_chunks=counters["transform_chunks"],
                transform_count=counters["transform_count"],
                validate_started=validate_started,
                validate_chunks=counters["validate_chunks"],
                validate_count=counters["validate_count"],
                validated_chunks=validated_chunks,
                dry_run=dry_run,
                transform_fn=self.transform,
                apply_transformers=self._apply_transformers,
                validate_fn=self.validate,
            )

        return counters, validated_chunks

    def _append_stage_result(
        self,
        stages_results: list[StageResult],
        stage: str,
        count: int,
        chunks: int,
    ) -> None:
        stages_results.append(
            self._stage_runner.make_stage_result(
                stage,
                count,
                chunks=chunks,
            )
        )
        self._hooks_manager.notify_stage_end(stage, stages_results[-1])

    def _perform_write_stage(
        self,
        context: RunContext,
        validated_chunks: list[pd.DataFrame],
        output_path: Path,
        counters: dict[str, int],
        stages_results: list[StageResult],
    ) -> tuple[WriteResult | None, dict[str, int]]:
        if not self._hooks_manager.get_stage_start("write"):
            self._hooks_manager.notify_stage_start("write", context)

        df_to_write = (
            pd.concat(validated_chunks, ignore_index=True)
            if validated_chunks
            else pd.DataFrame()
        )

        write_result = self._error_policy_manager.execute(
            "write",
            context,
            lambda: self.write(
                df_to_write,
                output_path,
                context,
            ),
        )
        if write_result is None:
            return None, counters

        counters["write_count"] = write_result.row_count
        counters["write_chunks"] = max(counters["validate_chunks"], 1)

        self._append_stage_result(
            stages_results,
            "write",
            write_result.row_count,
            counters["write_chunks"],
        )
        return write_result, counters

    # === Abstract Methods ===

    def get_database_version(self) -> str | None:
        """
        Возвращает версию базы данных источника.
        Может быть переопределено в наследниках.
        """
        return None

    # === Concrete Methods ===

    def get_version(self) -> str:
        """Возвращает версию источника данных. По умолчанию 'unknown'."""
        return "unknown"

    def extract(self, **kwargs: Any) -> pd.DataFrame:
        """Deprecated: used only if not iterating chunks."""
        if not self._extractor:
            return pd.DataFrame()

        chunks = list(self._extractor.extract(**kwargs))
        if not chunks:
            return pd.DataFrame()
        return pd.concat(chunks, ignore_index=True)

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """Преобразует сырые данные используя injected transformer."""  # noqa: E501
        if self._transformer:
            return self._transformer.apply(df)
        return df

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
        output_columns = self._validation_service.get_schema_columns(output_schema_name)

        return self._output_writer.write_result(
            df=df,
            output_path=output_path,
            entity_name=self._config.entity_name,
            run_context=context,
            column_order=output_columns,
        )

    def iter_chunks(self, **kwargs: Any) -> Iterable[pd.DataFrame]:
        """Возвращает итератор по чанкам данных после extract."""
        if self._extractor is not None:

            def _extractor_generator() -> Iterable[pd.DataFrame]:
                self._increment_extract_call_count()
                result = self._extractor.extract(**kwargs)
                if isinstance(result, pd.DataFrame):
                    yield result
                    return
                if isinstance(result, Iterable):
                    yield from result
                    return
                raise TypeError(
                    "Extractor.extract() must return DataFrame or iterable of "
                    "DataFrames."
                )

            return _extractor_generator()

        return self._iter_chunks_without_extractor(**kwargs)

    # === Hooks ===

    def add_hook(self, hook: PipelineHookABC) -> None:
        """Добавляет хук выполнения."""
        self._hooks_manager.add_hook(hook)

    def add_hooks(self, hooks: list[PipelineHookABC]) -> None:
        """Добавляет список хуков выполнения."""
        self._hooks_manager.add_hooks(hooks)

    def set_error_policy(self, error_policy: ErrorPolicyABC) -> None:
        """Устанавливает политику обработки ошибок."""
        self._error_policy = error_policy
        self._error_policy_manager = ErrorPolicyManager(
            error_policy=error_policy,
            hooks_manager=self._hooks_manager,
            logger=self._logger,
            provider_id=self._provider_id,
            entity_name=self._config.entity_name,
            default_on_skip=self._default_on_skip,
        )
        self._stage_runner = StageRunner(
            hooks_manager=self._hooks_manager,
            error_policy_manager=self._error_policy_manager,
            entity_name=self._config.entity_name,
            provider_id=self._provider_id,
        )

    def set_post_transformer(self, transformer: TransformerABC) -> None:
        """Позволяет заменить пост-обработчик трансформации."""
        self._post_transformer = transformer

    # === Internal Methods ===
    def _calculate_duration(self, context: RunContext) -> float:
        return (datetime.now(timezone.utc) - context.started_at).total_seconds()

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

    def _create_chunk_iterator(
        self, context: RunContext, **kwargs: Any
    ) -> Iterable[pd.DataFrame]:
        iterator = self._error_policy_manager.execute(
            "extract",
            context,
            lambda: self.iter_chunks(**kwargs),
        )
        if iterator is None:
            return iter([])
        if isinstance(iterator, pd.DataFrame):
            return iter([iterator])
        if not isinstance(iterator, Iterable):
            return iter([])
        return iter(iterator)

    def _run_stage(
        self,
        stage: str,
        context: RunContext,
        action: Callable[[], Any],
        *,
        attempt: int = 1,
    ) -> Any:
        self._hooks_manager.notify_stage_start(stage, context)
        return self._error_policy_manager.execute(
            stage,
            context,
            action,
            attempt=attempt,
        )

    def _default_on_skip(self, stage: str) -> Any:
        """Возвращает безопасное значение по умолчанию при пропуске стадии."""

        import pandas as pd  # pylint: disable=import-outside-toplevel

        if stage in {"extract", "transform", "validate"}:
            return pd.DataFrame()
        return None

    def _iter_chunks_without_extractor(self, **kwargs: Any) -> Iterable[pd.DataFrame]:
        """
        Fallback chunk iterator when external extractor is not provided.

        Uses subclass extract() implementation; raises if not overridden.
        """
        if self.__class__.extract is PipelineBase.extract:
            raise ValueError("Extractor is required when extract() is not overridden.")

        def _generator() -> Iterable[pd.DataFrame]:
            result = self.extract(**kwargs)
            if result is None:
                return
            if isinstance(result, pd.DataFrame):
                yield result
                return
            if isinstance(result, Iterable):
                yield from result
                return
            raise TypeError(
                "extract() must return a DataFrame or iterable of DataFrames."
            )

        return _generator()

    def _instrument_extract_calls(self) -> None:
        """
        Wraps extract() to expose call_count for tests without altering logic.

        The wrapper closes over the original bound extract, so self is preserved.
        """
        if getattr(self.extract, "call_count", None) is not None:
            return

        original_extract = self.extract

        def _wrapped_extract(*args: Any, **kwargs: Any) -> pd.DataFrame:
            _wrapped_extract.call_count += 1
            return original_extract(*args, **kwargs)

        _wrapped_extract.call_count = 0  # type: ignore[attr-defined]
        self.extract = _wrapped_extract  # type: ignore[assignment]

    def _increment_extract_call_count(self) -> None:
        """Helper to bump extract.call_count when using external extractor."""
        call_count = getattr(self.extract, "call_count", None)
        if call_count is not None:
            self.extract.call_count = call_count + 1  # type: ignore[attr-defined]

    def _enrich_context(self, context: RunContext) -> None:
        """
        Хук для обогащения контекста (например, добавления версии релиза).
        """

    def _record_stage_metrics(self, stage_result: StageResult, stage: str) -> None:
        outcome = self._determine_stage_outcome(stage, stage_result)
        metrics.STAGE_DURATION_SECONDS.labels(
            pipeline=self._config.id,
            provider=self._provider_id.value,
            entity=self._config.entity_name,
            stage=stage,
            outcome=outcome,
        ).observe(stage_result.duration_sec)
        metrics.STAGE_TOTAL.labels(
            pipeline=self._config.id,
            provider=self._provider_id.value,
            entity=self._config.entity_name,
            stage=stage,
            outcome=outcome,
        ).inc()

    def _determine_stage_outcome(self, stage: str, stage_result: StageResult) -> str:
        if not stage_result.success:
            return "error"

        action = self._error_policy_manager.get_last_action(stage)
        if action is not None and action == ErrorAction.SKIP:
            return "skip"
        return "success"
