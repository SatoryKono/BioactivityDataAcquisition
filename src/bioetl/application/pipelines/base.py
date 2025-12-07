"""Базовый класс пайплайна."""

from abc import ABC
from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any, Iterable, cast

import pandas as pd

from bioetl.application.pipelines.contracts import ExtractorABC
from bioetl.application.pipelines.run import PipelineRunnerFacade
from bioetl.application.pipelines.stage_runtime_manager import StageRuntimeManagerImpl
from bioetl.domain.clients.base.output.contracts import (
    RunMetadataBuilderProtocol,
    WriteResult,
)
from bioetl.domain.configs import PipelineConfig
from bioetl.domain.models import RunContext, RunResult
from bioetl.domain.observability import LoggingPortABC
from bioetl.domain.pipelines.contracts import ErrorPolicyABC, PipelineHookABC
from bioetl.domain.providers import ProviderId
from bioetl.domain.schemas.pipeline_contracts import get_pipeline_contract
from bioetl.domain.transform.contracts import HashServiceABC
from bioetl.domain.transform.factories import default_post_transformer
from bioetl.domain.transform.transformers import TransformerABC
from bioetl.domain.validation.service import ValidationService

if TYPE_CHECKING:
    from bioetl.domain.clients.base.output.contracts import OutputWriterABC


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
        output_writer: "OutputWriterABC",
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
        self._output_writer = output_writer
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

        self._runner = PipelineRunnerFacade(
            logger=self._logger,
            runtime_manager=self._runtime_manager,
            metadata_builder=self._metadata_builder,
            extract_stage=self,
            transform_stage=self,
            validate_stage=self,
            write_stage=self,
            apply_transformers=self._apply_transformers,
            context_builder=self._build_context,
            chunk_iterator_factory=self._create_chunk_iterator,
            reset_state=self._reset_hash_state,
        )

    # === Public API ===

    def run(
        self,
        output_path: Path,
        *,
        dry_run: bool = False,
        **kwargs: Any,
    ) -> RunResult:
        """Запускает полный цикл ETL-пайплайна."""
        return self._runner.run(output_path=output_path, dry_run=dry_run, **kwargs)

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

    def extract(
        self, context: RunContext | None = None, **kwargs: Any
    ) -> pd.DataFrame | Iterable[pd.DataFrame]:
        """Deprecated: used only if not iterating chunks."""
        if not self._extractor:
            return pd.DataFrame()

        chunks = list(self._extractor.extract(**kwargs))
        if not chunks:
            return pd.DataFrame()
        return pd.concat(chunks, ignore_index=True)

    def transform(
        self, df: pd.DataFrame, context: RunContext | None = None
    ) -> pd.DataFrame:
        """Преобразует сырые данные используя injected transformer."""  # noqa: E501
        if self._transformer:
            return self._transformer.apply(df)
        return df

    def validate(
        self, df: pd.DataFrame, context: RunContext | None = None
    ) -> pd.DataFrame:
        """Валидирует DataFrame по Pandera-схеме."""
        return self._validation_service.validate(
            df=df,
            entity_name=self._schema_contract.schema_out,
        )

    def write(
        self,
        df: pd.DataFrame,
        output_path: Path,
        context: RunContext | None = None,
    ) -> WriteResult:
        """Записывает валидированный DataFrame."""
        if context is None:
            raise ValueError("RunContext is required for write stage")
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
            extractor = self._extractor

            def _extractor_generator() -> Iterable[pd.DataFrame]:
                result = extractor.extract(**kwargs)
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
    def _apply_transformers(
        self, df: pd.DataFrame, context: RunContext
    ) -> pd.DataFrame:
        if not self._post_transformer:
            return df
        return self._post_transformer.apply(df, context)

    def _create_chunk_iterator(
        self, context: RunContext, params: dict[str, Any]
    ) -> Iterable[pd.DataFrame]:
        iterator = self._runtime_manager.execute_stage(
            "extract",
            context,
            lambda: self.iter_chunks(**params),
        )
        if iterator is None:
            return iter([])
        if isinstance(iterator, pd.DataFrame):
            return iter([iterator])
        if not isinstance(iterator, Iterable):
            return iter([])
        return iter(iterator)

    def _reset_hash_state(self) -> None:
        """Сбрасывает состояние сервисов хеширования перед запуском."""

        if hasattr(self._hash_service, "reset_state"):
            self._hash_service.reset_state()

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

    def _enrich_context(self, context: RunContext) -> None:
        """
        Хук для обогащения контекста (например, добавления версии релиза).
        """
