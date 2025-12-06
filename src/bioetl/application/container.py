"""Dependency Injection Container for the application."""

from pathlib import Path
from typing import Any, Callable

from bioetl.application.pipelines.hooks_impl import (
    FailFastErrorPolicyImpl,
    LoggingPipelineHookImpl,
    MetricsPipelineHookImpl,
)
from bioetl.config.pipeline_config_schema import PipelineConfig
from bioetl.domain.pipelines.contracts import ErrorPolicyABC, PipelineHookABC
from bioetl.domain.provider_registry import get_provider
from bioetl.domain.providers import ProviderDefinition, ProviderId
from bioetl.domain.record_source import ApiRecordSource, RecordSource
from bioetl.domain.schemas import register_schemas
from bioetl.domain.schemas.registry import SchemaRegistry
from bioetl.domain.transform.contracts import NormalizationServiceABC
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
from bioetl.infrastructure.clients.provider_registry_loader import (
    DEFAULT_PROVIDERS_CONFIG_PATH,
    ProviderRegistryLoader,
)
from bioetl.infrastructure.files.csv_record_source import (
    CsvRecordSourceImpl,
    IdListRecordSourceImpl,
)
from bioetl.infrastructure.logging.contracts import LoggerAdapterABC
from bioetl.infrastructure.logging.factories import default_logger
from bioetl.infrastructure.output.factories import (
    default_metadata_writer,
    default_quality_reporter,
    default_writer,
)
from bioetl.infrastructure.output.unified_writer import UnifiedOutputWriter


class PipelineContainer:
    """
    DI Container for pipeline dependencies.
    """

    def __init__(
        self,
        config: PipelineConfig,
        *,
        logger: LoggerAdapterABC | None = None,
        hooks: list[PipelineHookABC] | None = None,
        error_policy: ErrorPolicyABC | None = None,
        hash_service: HashService | None = None,
        post_transformer: TransformerABC | None = None,
        providers_config_path: str | Path | None = None,
    ) -> None:
        self.config = config
        self._provider_id = ProviderId(self.config.provider)
        self._schema_registry = SchemaRegistry()
        self._logger: LoggerAdapterABC | None = logger
        self._hooks: list[PipelineHookABC] | None = list(hooks) if hooks else None
        self._error_policy: ErrorPolicyABC | None = error_policy
        self._hash_service: HashService | None = hash_service
        self._post_transformer: TransformerABC | None = post_transformer
        self._providers_config_path = providers_config_path
        register_schemas(self._schema_registry)
        self._register_providers()

    def get_logger(self) -> LoggerAdapterABC:
        """Get the configured logger."""
        if self._logger is None:
            self._logger = default_logger()
        return self._logger

    def get_validation_service(self) -> ValidationService:
        """Get the validation service with registered schemas."""
        return ValidationService(schema_provider=self._schema_registry)

    def get_output_writer(self) -> UnifiedOutputWriter:
        """Get the unified output writer."""
        return UnifiedOutputWriter(
            writer=default_writer(),
            metadata_writer=default_metadata_writer(),
            quality_reporter=default_quality_reporter(),
            config=self.config.determinism,
            qc_config=self.config.qc,
        )

    def get_normalization_service(self) -> NormalizationServiceABC:
        """Create normalization service for the configured provider."""

        definition = self._get_provider_definition()
        source_config = self._resolve_provider_config(definition)
        components = definition.components

        factory = getattr(components, "create_normalization_service", None)
        if factory is None:
            raise ValueError(
                f"Unsupported provider for normalization: {self._provider_id.value}"
            )
        return factory(source_config, pipeline_config=self.config)

    def get_record_source(
        self,
        extraction_service: Any,
        *,
        limit: int | None = None,
        logger: LoggerAdapterABC | None = None,
    ) -> RecordSource:
        """Create record source based on pipeline input configuration."""
        mode = self.config.input_mode
        path = self.config.input_path

        if mode == "auto_detect" and path:
            mode = "csv"

        effective_logger = logger or self.get_logger()

        if mode == "csv":
            if path is None:
                raise ValueError("input_path is required for CSV mode")
            return CsvRecordSourceImpl(
                input_path=Path(path),
                csv_options=self.config.csv_options,
                limit=limit,
                logger=effective_logger,
            )

        if mode == "id_only":
            if path is None:
                raise ValueError("input_path is required for ID-only mode")
            definition = self._get_provider_definition()
            source_config = self._resolve_provider_config(definition)
            id_column = self._resolve_primary_key()
            filter_key = f"{id_column}__in"
            return IdListRecordSourceImpl(
                input_path=Path(path),
                id_column=id_column,
                csv_options=self.config.csv_options,
                limit=limit,
                extraction_service=extraction_service,
                source_config=source_config,
                entity=self.config.entity_name,
                filter_key=filter_key,
                logger=effective_logger,
            )

        filters = self.config.pipeline.copy()
        if limit is not None:
            filters["limit"] = limit

        return ApiRecordSource(
            extraction_service=extraction_service,
            entity=self.config.entity_name,
            filters=filters,
            chunk_size=self.config.batch_size,
        )

    def get_extraction_service(self) -> Any:
        """Get the extraction service based on provider configuration."""
        definition = self._get_provider_definition()
        source_config = self._resolve_provider_config(definition)

        client = definition.components.create_client(source_config)
        return definition.components.create_extraction_service(
            source_config, client=client
        )

    def get_hash_service(self) -> HashService:
        """Get the hash service."""
        if self._hash_service is None:
            self._hash_service = HashService()
        return self._hash_service

    def get_post_transformer(
        self, *, version_provider: Callable[[], str] | None = None
    ) -> TransformerABC:
        """Собирает цепочку стандартных трансформеров."""
        if self._post_transformer is None:
            hash_service = self.get_hash_service()
            provider = version_provider or (lambda: "unknown")
            self._post_transformer = TransformerChain(
                [
                    HashColumnsTransformer(
                        hash_service, self.config.hashing.business_key_fields
                    ),
                    IndexColumnTransformer(hash_service),
                    DatabaseVersionTransformer(hash_service, provider),
                    FulldateTransformer(hash_service),
                ]
            )
        return self._post_transformer

    def get_hooks(self) -> list[PipelineHookABC]:
        """Возвращает список хуков выполнения пайплайна."""
        if self._hooks is None:
            self._hooks = [
                LoggingPipelineHookImpl(self.get_logger()),
                MetricsPipelineHookImpl(
                    pipeline_id=self.config.id,
                    provider=self._provider_id.value,
                    entity_name=self.config.entity_name,
                ),
            ]
        return list(self._hooks)

    def get_error_policy(self) -> ErrorPolicyABC:
        """Возвращает политику обработки ошибок пайплайна."""
        if self._error_policy is None:
            self._error_policy = FailFastErrorPolicyImpl()
        return self._error_policy

    def _resolve_primary_key(self) -> str:
        pk = self.config.primary_key
        if not pk and self.config.pipeline and "primary_key" in self.config.pipeline:
            pk = self.config.pipeline["primary_key"]
        if not pk:
            pk = f"{self.config.entity_name}_id"
        if not pk:
            raise ValueError(
                f"Could not resolve primary key for entity '{self.config.entity_name}'"
            )
        return pk

    def _register_providers(self) -> None:
        providers_config_path = getattr(
            self, "_providers_config_path", DEFAULT_PROVIDERS_CONFIG_PATH
        )
        # object.__new__ в тестах не вызывает __init__, поэтому поднимаем
        # резервный логгер, если атрибут ещё не создан.
        logger = getattr(self, "_logger", None)
        if logger is None:
            logger = default_logger()
            # сохраняем, чтобы последующие вызовы get_logger не падали
            self._logger = logger
        loader = ProviderRegistryLoader(providers_config_path, logger=logger)
        loader.load()

    def _get_provider_definition(self) -> ProviderDefinition:
        return get_provider(self._provider_id)

    def _resolve_provider_config(self, definition: ProviderDefinition) -> Any:
        source_config = self.config.get_source_config(self._provider_id.value)
        if not isinstance(source_config, definition.config_type):
            raise TypeError(
                f"Expected config type {definition.config_type.__name__} for "
                f"provider '{self._provider_id.value}'"
            )
        return source_config


def build_pipeline_dependencies(
    config: PipelineConfig,
    *,
    logger: LoggerAdapterABC | None = None,
    hooks: list[PipelineHookABC] | None = None,
    error_policy: ErrorPolicyABC | None = None,
    hash_service: HashService | None = None,
    post_transformer: TransformerABC | None = None,
    providers_config_path: str | Path | None = None,
) -> PipelineContainer:
    """Factory for the container."""
    return PipelineContainer(
        config,
        logger=logger,
        hooks=hooks,
        error_policy=error_policy,
        hash_service=hash_service,
        post_transformer=post_transformer,
        providers_config_path=providers_config_path,
    )
