"""Dependency Injection Container for the application."""

from pathlib import Path
from typing import Any, Callable, cast

from bioetl.application.pipelines.contracts import PipelineContainerABC
from bioetl.application.pipelines.hooks_impl import (
    FailFastErrorPolicyImpl,
    LoggingPipelineHookImpl,
    MetricsPipelineHookImpl,
)
from bioetl.domain.clients.base.logging.contracts import LoggerAdapterABC
from bioetl.domain.clients.base.output.contracts import (
    MetadataWriterABC,
    QualityReportABC,
    WriterABC,
)
from bioetl.domain.configs import PipelineConfig
from bioetl.domain.pipelines.contracts import ErrorPolicyABC, PipelineHookABC
from bioetl.domain.provider_registry import ProviderRegistryABC
from bioetl.domain.providers import ProviderDefinition, ProviderId
from bioetl.domain.record_source import ApiRecordSource, RecordSource
from bioetl.domain.schemas import register_schemas
from bioetl.domain.schemas.registry import SchemaRegistry
from bioetl.domain.transform.contracts import NormalizationServiceABC
from bioetl.domain.transform.factories import default_post_transformer
from bioetl.domain.transform.hash_service import HashService
from bioetl.domain.transform.transformers import TransformerABC
from bioetl.domain.validation.service import ValidationService
from bioetl.infrastructure.files.csv_record_source import (
    CsvRecordSourceImpl,
    IdListRecordSourceImpl,
)
from bioetl.infrastructure.logging.factories import default_logger
from bioetl.infrastructure.output.factories import (
    default_metadata_writer,
    default_quality_reporter,
    default_writer,
)
from bioetl.infrastructure.output.unified_writer import UnifiedOutputWriter


class PipelineContainer(PipelineContainerABC):
    """
    DI Container for pipeline dependencies.
    """

    def __init__(
        self,
        config: PipelineConfig,
        *,
        logger: LoggerAdapterABC | None = None,
        writer: WriterABC | None = None,
        metadata_writer: MetadataWriterABC | None = None,
        quality_reporter: QualityReportABC | None = None,
        hooks: list[PipelineHookABC] | None = None,
        error_policy: ErrorPolicyABC | None = None,
        hash_service: HashService | None = None,
        post_transformer: TransformerABC | None = None,
        provider_registry: ProviderRegistryABC | None = None,
        provider_registry_provider: Callable[[], ProviderRegistryABC] | None = None,
    ) -> None:
        self._config = config
        self._provider_id = ProviderId(self._config.provider)
        self._schema_registry = SchemaRegistry()
        self._logger: LoggerAdapterABC = logger or default_logger()
        self._writer: WriterABC = writer or default_writer()
        self._metadata_writer: MetadataWriterABC = (
            metadata_writer or default_metadata_writer()
        )
        self._quality_reporter: QualityReportABC = (
            quality_reporter or default_quality_reporter()
        )
        self._hooks: list[PipelineHookABC] | None = list(hooks) if hooks else None
        self._error_policy: ErrorPolicyABC | None = error_policy
        self._hash_service: HashService | None = hash_service
        self._post_transformer: TransformerABC | None = post_transformer
        self._provider_registry = provider_registry
        self._provider_registry_provider = provider_registry_provider
        if self._provider_registry is None and self._provider_registry_provider is None:
            raise ValueError(
                "Provider registry must be supplied (instance or provider callable)"
            )
        self._output_writer = UnifiedOutputWriter(
            writer=self._writer,
            metadata_writer=self._metadata_writer,
            quality_reporter=self._quality_reporter,
            config=self._config.determinism,
            qc_config=self._config.qc,
        )
        register_schemas(self._schema_registry)

    @property
    def config(self) -> PipelineConfig:
        return self._config

    def get_logger(self) -> LoggerAdapterABC:
        """Get the configured logger."""
        return self._logger

    def get_validation_service(self) -> ValidationService:
        """Get the validation service with registered schemas."""
        return ValidationService(schema_provider=self._schema_registry)

    def get_output_writer(self) -> UnifiedOutputWriter:
        """Get the unified output writer."""
        return self._output_writer

    def get_normalization_service(self) -> NormalizationServiceABC:
        """Create normalization service for the configured provider."""

        definition = self._get_provider_definition()
        source_config = self._resolve_provider_config(definition)
        components = definition.components

        factory = cast(
            Callable[..., NormalizationServiceABC] | None,
            getattr(components, "create_normalization_service", None),
        )
        if factory is None:
            raise ValueError(
                f"Unsupported provider for normalization: {self._provider_id.value}"
            )
        return factory(source_config, pipeline_config=self._config)

    def get_record_source(
        self,
        extraction_service: Any,
        *,
        limit: int | None = None,
        logger: LoggerAdapterABC | None = None,
    ) -> RecordSource:
        """Create record source based on pipeline input configuration."""
        mode = self._config.input_mode
        path = self._config.input_path

        if mode == "auto_detect" and path:
            mode = "csv"

        effective_logger = logger or self.get_logger()

        if mode == "csv":
            if path is None:
                raise ValueError("input_path is required for CSV mode")
            return CsvRecordSourceImpl(
                input_path=Path(path),
                csv_options=self._config.csv_options,
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
                csv_options=self._config.csv_options,
                limit=limit,
                extraction_service=extraction_service,
                source_config=source_config,
                entity=self._config.entity_name,
                filter_key=filter_key,
                logger=effective_logger,
            )

        filters = self._config.pipeline.copy()
        if limit is not None:
            filters["limit"] = limit

        return ApiRecordSource(
            extraction_service=extraction_service,
            entity=self._config.entity_name,
            filters=filters,
            chunk_size=self._config.batch_size,
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
            self._post_transformer = default_post_transformer(
                hash_service=self.get_hash_service(),
                business_key_fields=self._config.hashing.business_key_fields,
                version_provider=version_provider,
            )
        return self._post_transformer

    def get_hooks(self) -> list[PipelineHookABC]:
        """Возвращает список хуков выполнения пайплайна."""
        if self._hooks is None:
            self._hooks = [
                LoggingPipelineHookImpl(self.get_logger()),
                MetricsPipelineHookImpl(
                    pipeline_id=self._config.id,
                    provider=self._provider_id.value,
                    entity_name=self._config.entity_name,
                ),
            ]
        return list(self._hooks)

    def get_error_policy(self) -> ErrorPolicyABC:
        """Возвращает политику обработки ошибок пайплайна."""
        if self._error_policy is None:
            self._error_policy = FailFastErrorPolicyImpl()
        return self._error_policy

    def _resolve_primary_key(self) -> str:
        pk = self._config.primary_key
        if not pk and self._config.pipeline and "primary_key" in self._config.pipeline:
            pk = self._config.pipeline["primary_key"]
        if not pk:
            pk = f"{self._config.entity_name}_id"
        if not pk:
            raise ValueError(
                f"Could not resolve primary key for entity '{self._config.entity_name}'"
            )
        return pk

    def _get_provider_definition(self) -> ProviderDefinition:
        return self._get_provider_registry().get_provider(self._provider_id)

    def _get_provider_registry(self) -> ProviderRegistryABC:
        if self._provider_registry is not None:
            return self._provider_registry
        if self._provider_registry_provider is None:
            raise RuntimeError("Provider registry provider is not configured")

        self._provider_registry = self._provider_registry_provider()
        if self._provider_registry is None:
            raise RuntimeError("Provider registry provider returned None")

        return self._provider_registry

    def _resolve_provider_config(self, definition: ProviderDefinition) -> Any:
        source_config = self._config.get_source_config(self._provider_id.value)
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
    writer: WriterABC | None = None,
    metadata_writer: MetadataWriterABC | None = None,
    quality_reporter: QualityReportABC | None = None,
    hooks: list[PipelineHookABC] | None = None,
    error_policy: ErrorPolicyABC | None = None,
    hash_service: HashService | None = None,
    post_transformer: TransformerABC | None = None,
    provider_registry: ProviderRegistryABC | None = None,
    provider_registry_provider: Callable[[], ProviderRegistryABC] | None = None,
) -> PipelineContainerABC:
    """Factory for the container."""
    return PipelineContainer(
        config,
        logger=logger,
        writer=writer,
        metadata_writer=metadata_writer,
        quality_reporter=quality_reporter,
        hooks=hooks,
        error_policy=error_policy,
        hash_service=hash_service,
        post_transformer=post_transformer,
        provider_registry=provider_registry,
        provider_registry_provider=provider_registry_provider,
    )
