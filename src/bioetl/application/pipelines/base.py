"""Базовый класс пайплайна."""

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable, Iterable, cast

import pandas as pd

from bioetl.application.pipelines.contracts import ExtractorABC, LoaderABC
from bioetl.application.pipelines.stage_runtime_manager import StageRuntimeManagerImpl
from bioetl.domain.clients.base.output.contracts import (
    RunMetadataBuilderProtocol,
    WriteResult,
)
from bioetl.domain.configs import PipelineConfig
from bioetl.domain.errors import PipelineStageError
from bioetl.domain.models import RunContext, RunResult, StageResult
from bioetl.domain.observability import LoggingPortABC
from bioetl.domain.pipelines.contracts import ErrorPolicyABC, PipelineHookABC
from bioetl.domain.providers import ProviderId
from bioetl.domain.schemas.pipeline_contracts import get_pipeline_contract
from bioetl.domain.transform.contracts import HashServiceABC
from bioetl.domain.transform.factories import default_post_transformer
from bioetl.domain.transform.transformers import TransformerABC
from bioetl.domain.validation.service import ValidationService

def _create_default_metadata_builder() -> RunMetadataBuilderProtocol:
    """Fallback metadata builder for cases when container is not provided."""

    return cast(
        RunMetadataBuilderProtocol,
        SimpleNamespace(
            build_run_metadata=lambda context, write_result: {
                "run_id": getattr(context, "run_id", None),
                "provider": getattr(context, "provider", None),
                "entity": getattr(context, "entity_name", None),
                "row_count": getattr(write_result, "row_count", 0),
                "dry_run": False,
            },
            build_dry_run_metadata=lambda context, row_count: {
                "run_id": getattr(context, "run_id", None),
                "provider": getattr(context, "provider", None),
                "entity": getattr(context, "entity_name", None),
                "row_count": row_count,
                "dry_run": True,
            },
        ),
    )


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
        logger: LoggingPortABC,
        validation_service: ValidationService,
        loader: LoaderABC,
        hash_service: HashServiceABC,
        metadata_builder: RunMetadataBuilderProtocol | None = None,
        extractor: ExtractorABC | None = None,
        hooks: list[PipelineHookABC] | None = None,
        error_policy: ErrorPolicyABC | None = None,
        transformer: TransformerABC | None = None,
        post_transformer: TransformerABC | None = None,
    ) -> None:
        self._config = config
        self._provider_id = ProviderId(config.provider)
        self._logger = logger.apply_bind(
            entity=config.entity_name,
            provider=self._provider_id.value,
            pipeline=config.id,
        )
        self._validation_service = validation_service
        self._loader = loader
        self._hash_service = hash_service
        self._metadata_builder = metadata_builder or _create_default_metadata_builder()
        self._extractor = extractor
        self._transformer = transformer
        self._post_transformer = post_transformer
        if self._post_transformer is None:
            business_key_fields = self._resolve_business_key_fields()
            self._post_transformer = default_post_transformer(
                hash_service=self._hash_service,
                business_key_fields=business_key_fields,
                version_provider=self.get_version,
            )
        self._schema_contract = get_pipeline_contract(
            config.id, default_entity=config.entity_name
        )
        from bioetl.application.pipelines.hooks_impl import (  # pylint: disable=import-outside-toplevel
            FailFastErrorPolicyImpl,
        )

        self._error_policy = error_policy or FailFastErrorPolicyImpl()
        self._runtime_manager = StageRuntimeManagerImpl(
            logger=self._logger,
            provider_id=self._provider_id,
            entity_name=self._config.entity_name,
            error_policy=self._error_policy,
            default_on_skip=self._default_on_skip,
            hooks=hooks,
            pipeline_id=self._config.id,
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
        """Запускает полный цикл ETL-пайплайна."""
        self._runtime_manager.reset()
        if hasattr(self._hash_service, "reset_state"):
            self._hash_service.reset_state()

        context = self._build_context(dry_run)
        self._logger = self._logger.apply_bind(run_id=context.run_id)
        self._runtime_manager.set_logger(self._logger)
        self._logger.info("Pipeline started", run_id=context.run_id)
        stages_results: list[StageResult] = []
        counters = self._init_stage_counters()
        validated_chunks: list[pd.DataFrame] = []

        try:
            self._runtime_manager.notify_stage_start("extract", context)
            counters, validated_chunks = self._process_extract_stage(
                context, counters, validated_chunks, dry_run, kwargs
            )

            self._append_stage_result(
                stages_results,
                "extract",
                counters["extract_count"],
                counters["extract_chunks"],
            )

            self._append_stage_result(
                stages_results,
                "transform",
                counters["transform_count"],
                counters["transform_chunks"],
            )

            self._append_stage_result(
                stages_results,
                "validate",
                counters["validate_count"],
                counters["validate_chunks"],
            )

            write_result: WriteResult | None = None
            if not dry_run:
                write_result, counters = self._perform_write_stage(
                    context, validated_chunks, output_path, counters, stages_results
                )
                if write_result is None:
                    run_result = self._runtime_manager.handle_stage_failure(
                        "write", stages_results, context
                    )
                    return run_result

            meta_raw = (
                self._metadata_builder.build_run_metadata(context, write_result)
                if write_result
                else self._metadata_builder.build_dry_run_metadata(
                    context, counters["validate_count"]
                )
            )
            meta = self._normalize_meta(
                meta_raw, context, counters["validate_count"], dry_run
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
            stage_result = self._runtime_manager.make_stage_result(
                error.stage,
                0,
                success=False,
                errors=self._runtime_manager.get_last_error_messages(),
            )
            stages_results.append(stage_result)
            self._runtime_manager.notify_stage_end(error.stage, stage_result)
            self._logger.error(
                "Pipeline failed",
                stage=error.stage,
                provider=error.provider,
                entity=error.entity,
                run_id=error.run_id,
                error=str(error.cause) if error.cause else str(error),
            )
            raise

    def _resolve_business_key_fields(self) -> list[str] | None:
        """Возвращает бизнес-ключи из конфига с поддержкой legacy-полей."""

        hashing_section = getattr(self._config, "hashing", None)
        if isinstance(hashing_section, property):
            hashing_section = (
                hashing_section.fget(self._config) if hashing_section.fget else None
            )

        if hashing_section is None or isinstance(hashing_section, property):
            hashing_section = getattr(
                getattr(self._config, "quality", None), "hashing", None
            )

        fields = getattr(hashing_section, "business_key_fields", None)
        if fields is None:
            return None

        return list(fields)

    def _build_context(self, dry_run: bool) -> RunContext:
        context = RunContext(
            entity_name=self._config.entity_name,
            provider=self._provider_id.value,
            config=self._config.model_dump(),
            dry_run=dry_run,
        )
        self._enrich_context(context)
        return context

    def _normalize_meta(
        self, meta: dict[str, Any], context: RunContext, row_count: int, dry_run: bool
    ) -> dict[str, Any]:
        """
        Ensures required metadata fields are present even with minimal builders.
        """
        if not isinstance(meta, dict):
            raise TypeError("Metadata builder must return a dict.")

        normalized_meta = dict(meta)
        normalized_meta.setdefault("run_id", context.run_id)
        normalized_meta.setdefault("provider", context.provider)
        normalized_meta.setdefault("entity", context.entity_name)
        normalized_meta.setdefault("row_count", row_count)
        if dry_run:
            normalized_meta["dry_run"] = True
        else:
            normalized_meta.setdefault("dry_run", False)

        return normalized_meta

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
            """Recreate extractor iterator for retries."""
            nonlocal chunk_iterator
            chunk_iterator = self._create_chunk_iterator(context, **kwargs)

        reset_iterator()
        while True:
            try:
                raw_chunk_obj = self._runtime_manager.execute_stage(
                    "extract",
                    context,
                    lambda: next(chunk_iterator),  # type: ignore
                    on_retry=reset_iterator,
                )
            except StopIteration:
                break

            counters["extract_chunks"] += 1
            if raw_chunk_obj is None:
                raw_chunk: pd.DataFrame = pd.DataFrame()
            elif isinstance(raw_chunk_obj, pd.DataFrame):
                raw_chunk = raw_chunk_obj
            else:
                raise TypeError("Extractor must yield pandas DataFrame chunks.")
            counters["extract_count"] += len(raw_chunk)

            (
                transform_started,
                counters["transform_chunks"],
                counters["transform_count"],
                validate_started,
                counters["validate_chunks"],
                counters["validate_count"],
            ) = self._runtime_manager.process_chunk(
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
            ) = self._runtime_manager.process_chunk(
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
            self._runtime_manager.make_stage_result(
                stage,
                count,
                chunks=chunks,
            )
        )
        self._runtime_manager.notify_stage_end(stage, stages_results[-1])

    def _perform_write_stage(
        self,
        context: RunContext,
        validated_chunks: list[pd.DataFrame],
        output_path: Path,
        counters: dict[str, int],
        stages_results: list[StageResult],
    ) -> tuple[WriteResult | None, dict[str, int]]:
        if not self._runtime_manager.get_stage_start("write"):
            self._runtime_manager.notify_stage_start("write", context)

        df_to_write = (
            pd.concat(validated_chunks, ignore_index=True)
            if validated_chunks
            else pd.DataFrame()
        )

        write_result_obj = self._runtime_manager.execute_stage(
            "write",
            context,
            lambda: self.write(
                df_to_write,
                output_path,
                context,
            ),
        )
        if write_result_obj is None:
            return None, counters
        if not isinstance(write_result_obj, WriteResult):
            raise TypeError("Writer must return WriteResult or None.")
        write_result = write_result_obj

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

    @abstractmethod
    def extract(
        self, **kwargs: Any
    ) -> pd.DataFrame | Iterable[pd.DataFrame] | None:
        """Извлекает сырые данные."""

    @abstractmethod
    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """Преобразует сырые данные."""

    def validate(self, df: pd.DataFrame) -> pd.DataFrame:
        """Валидирует DataFrame по Pandera-схеме."""
        return self._validation_service.validate(
            df=df,
            entity_name=self._schema_contract.schema_out,
        )

    @abstractmethod
    def write(
        self,
        df: pd.DataFrame,
        output_path: Path,
        context: RunContext,
    ) -> WriteResult:
        """Записывает валидированный DataFrame."""
        output_schema_name = self._schema_contract.get_output_schema()
        output_columns = self._validation_service.get_schema_columns(output_schema_name)

        return self._loader.load(
            df=df,
            output_path=output_path,
            context=context,
            column_order=output_columns,
        )

    def iter_chunks(self, **kwargs: Any) -> Iterable[pd.DataFrame]:
        """Возвращает итератор по чанкам данных после extract."""

        def _extractor_generator() -> Iterable[pd.DataFrame]:
            self._increment_extract_call_count()
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

        return _extractor_generator()

    # === Hooks ===

    def register_hook(self, hook: PipelineHookABC) -> None:
        """Добавляет хук выполнения."""
        self._runtime_manager.register_hook(hook)

    def register_hooks(self, hooks: list[PipelineHookABC]) -> None:
        """Добавляет список хуков выполнения."""
        self._runtime_manager.register_hooks(hooks)

    def set_error_policy(self, error_policy: ErrorPolicyABC) -> None:
        """Устанавливает политику обработки ошибок."""
        self._error_policy = error_policy
        self._runtime_manager.set_error_policy(error_policy)

    def set_post_transformer(self, transformer: TransformerABC) -> None:
        """Позволяет заменить пост-обработчик трансформации."""
        self._post_transformer = transformer

    # === Internal Methods ===
    def _calculate_duration(self, context: RunContext) -> float:
        return (datetime.now(timezone.utc) - context.started_at).total_seconds()

    def _apply_transformers(
        self, df: pd.DataFrame, context: RunContext
    ) -> pd.DataFrame:
        if not self._post_transformer:
            return df
        return self._post_transformer.apply(df, context)

    def _write_output(
        self, df: pd.DataFrame, output_path: Path, context: RunContext
    ) -> WriteResult:
        output_schema_name = self._schema_contract.get_output_schema()
        output_columns = self._validation_service.get_schema_columns(output_schema_name)

        return self._output_writer.write_result(
            df=df,
            output_path=output_path,
            entity_name=self._config.entity_name,
            run_context=context,
            column_order=output_columns,
        )

    def _create_chunk_iterator(
        self, context: RunContext, **kwargs: Any
    ) -> Iterable[pd.DataFrame]:
        iterator = self._runtime_manager.execute_stage(
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
        self._runtime_manager.notify_stage_start(stage, context)
        return self._runtime_manager.execute_stage(
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

    def _instrument_extract_calls(self) -> None:
        """
        Wraps extract() to expose call_count for tests without altering logic.

        The wrapper closes over the original bound extract, so self is preserved.
        """
        if getattr(self.extract, "call_count", None) is not None:
            return

        original_extract = self.extract

        def _wrapped_extract(*args: Any, **kwargs: Any) -> pd.DataFrame:
            call_count = getattr(_wrapped_extract, "call_count", 0)
            setattr(_wrapped_extract, "call_count", call_count + 1)
            return original_extract(*args, **kwargs)

        setattr(_wrapped_extract, "call_count", 0)
        self.extract = _wrapped_extract  # type: ignore[method-assign]

    def _increment_extract_call_count(self) -> None:
        """Helper to bump extract.call_count when using external extractor."""
        call_count = getattr(self.extract, "call_count", None)
        if isinstance(call_count, int):
            setattr(self.extract, "call_count", call_count + 1)

    def _enrich_context(self, context: RunContext) -> None:
        """
        Хук для обогащения контекста (например, добавления версии релиза).
        """
