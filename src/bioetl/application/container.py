"""Dependency Injection Container for the application."""

from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable, cast

from bioetl.application.pipelines.contracts import (
    FileRecordSourceFactoryABC,
    PipelineContainerABC,
)
from bioetl.application.pipelines.hooks_impl import (
    FailFastErrorPolicyImpl,
    LoggingPipelineHookImpl,
    MetricsPipelineHookImpl,
)
from bioetl.application.transform.pandas_batch_adapter import PandasBatchAdapter
from bioetl.domain.clients.base.output.contracts import (
    MetadataWriterABC,
    OutputWriterABC,
    QualityReportABC,
    RunMetadataBuilderProtocol,
    WriterABC,
    WriteResult,
)
from bioetl.domain.configs import PipelineConfig
from bioetl.domain.observability import LoggingPortABC, PipelineMetricsPortABC
from bioetl.domain.pipelines.contracts import ErrorPolicyABC, PipelineHookABC
from bioetl.domain.provider_registry import ProviderRegistryABC
from bioetl.domain.providers import ProviderDefinition, ProviderId
from bioetl.domain.record_source import ApiRecordSource, InMemoryRecordSource, RecordSource
from bioetl.domain.schemas import register_schemas
from bioetl.domain.schemas.registry import SchemaRegistry
from bioetl.domain.transform.contracts import HashServiceABC, NormalizationServiceABC
from bioetl.domain.transform.factories import default_post_transformer
from bioetl.domain.transform.hash_service import HashService
from bioetl.domain.transform.transformers import TransformerABC
from bioetl.domain.validation import SchemaProviderABC, ValidatorFactoryABC
from bioetl.domain.validation.contracts import ValidationResult
from bioetl.domain.validation.service import ValidationService


class PipelineContainer(PipelineContainerABC):
    """
    DI Container for pipeline dependencies.
    """

    def __init__(
        self,
        config: PipelineConfig,
        *,
        logger: LoggingPortABC | None = None,
        output_writer: OutputWriterABC | None = None,
        writer: WriterABC | None = None,
        metadata_writer: MetadataWriterABC | None = None,
        quality_reporter: QualityReportABC | None = None,
        validator_factory: ValidatorFactoryABC | None = None,
        record_source_factory: FileRecordSourceFactoryABC | None = None,
        metadata_builder: RunMetadataBuilderProtocol | None = None,
        metrics_port: PipelineMetricsPortABC | None = None,
        hooks: list[PipelineHookABC] | None = None,
        error_policy: ErrorPolicyABC | None = None,
        hash_service: HashServiceABC | None = None,
        post_transformer: TransformerABC | None = None,
        provider_registry: ProviderRegistryABC | None = None,
        provider_registry_provider: Callable[[], ProviderRegistryABC] | None = None,
        schema_provider: SchemaProviderABC | None = None,
    ) -> None:
        self._config = config
        self._provider_id = ProviderId(self._config.provider)
        self._schema_provider: SchemaProviderABC = self._resolve_schema_provider(
            schema_provider
        )
        self._validator_factory = self._resolve_validator_factory(validator_factory)
        self._logger = self._resolve_logger(logger)
        self._hooks: list[PipelineHookABC] | None = list(hooks) if hooks else None
        self._error_policy = error_policy
        self._hash_service = hash_service
        self._post_transformer = post_transformer
        self._record_source_factory = self._resolve_record_source_factory(
            record_source_factory
        )
        self._metadata_builder = self._resolve_metadata_builder(metadata_builder)
        self._metrics_port = self._resolve_metrics_port(metrics_port)
        self._provider_registry, self._provider_registry_provider = (
            self._resolve_provider_registry(
                provider_registry, provider_registry_provider
            )
        )
        self._output_writer = output_writer or _create_noop_output_writer()
        register_schemas(self._schema_provider)

    def _resolve_schema_provider(
        self, schema_provider: SchemaProviderABC | None
    ) -> SchemaProviderABC:
        return schema_provider or SchemaRegistry()

    def _resolve_validator_factory(
        self, validator_factory: ValidatorFactoryABC | None
    ) -> ValidatorFactoryABC:
        return validator_factory or _create_noop_validator_factory()

    def _resolve_logger(self, logger: LoggingPortABC | None) -> LoggingPortABC:
        return logger or _create_noop_logger()

    def _resolve_record_source_factory(
        self, record_source_factory: FileRecordSourceFactoryABC | None
    ) -> FileRecordSourceFactoryABC:
        return record_source_factory or _create_noop_record_source_factory()

    def _resolve_metadata_builder(
        self, metadata_builder: RunMetadataBuilderProtocol | None
    ) -> RunMetadataBuilderProtocol:
        return metadata_builder or _create_noop_metadata_builder()

    def _resolve_metrics_port(
        self, metrics_port: PipelineMetricsPortABC | None
    ) -> PipelineMetricsPortABC:
        return metrics_port or _create_noop_metrics_port()

    def _resolve_provider_registry(
        self,
        provider_registry: ProviderRegistryABC | None,
        provider_registry_provider: Callable[[], ProviderRegistryABC] | None,
    ) -> tuple[ProviderRegistryABC | None, Callable[[], ProviderRegistryABC] | None]:
        if provider_registry is None and provider_registry_provider is None:
            raise ValueError(
                "Provider registry must be supplied (instance or provider callable)"
            )
        return provider_registry, provider_registry_provider

    @property
    def config(self) -> PipelineConfig:
        """Return the pipeline configuration."""
        return self._config

    def get_logger(self) -> LoggingPortABC:
        """Get the configured logger."""
        return self._logger

    def get_validation_service(self) -> ValidationService:
        """Get the validation service with registered schemas."""
        return ValidationService(
            schema_provider=self._schema_provider,
            validator_factory=self._validator_factory,
        )

    def get_output_writer(self) -> OutputWriterABC:
        """Get the unified output writer."""
        return self._output_writer

    def get_record_source_factory(self) -> FileRecordSourceFactoryABC:
        """Expose record source factory port."""
        return self._record_source_factory

    def get_metadata_builder(self) -> RunMetadataBuilderProtocol:
        """Get metadata builder port."""
        return self._metadata_builder

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
        logger: LoggingPortABC | None = None,
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
            return self._record_source_factory.create_csv_source(
                input_path=Path(path),
                csv_options=self._config.csv_options,
                limit=limit,
                chunk_size=None,
                logger=effective_logger,
            )

        if mode == "id_only":
            if path is None:
                raise ValueError("input_path is required for ID-only mode")
            definition = self._get_provider_definition()
            source_config = self._resolve_provider_config(definition)
            id_column = self._resolve_primary_key()
            filter_key = f"{id_column}__in"
            return self._record_source_factory.create_id_list_source(
                input_path=Path(path),
                id_column=id_column,
                csv_options=self._config.csv_options,
                limit=limit,
                chunk_size=None,
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
            batch_adapter=PandasBatchAdapter().process_batch,
        )

    def get_extraction_service(self) -> Any:
        """Get the extraction service based on provider configuration."""
        definition = self._get_provider_definition()
        source_config = self._resolve_provider_config(definition)

        client = definition.components.create_client(source_config)
        return definition.components.create_extraction_service(
            source_config, client=client
        )

    def get_hash_service(self) -> HashServiceABC:
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
                    metrics_port=self._metrics_port,
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


def _create_noop_logger() -> LoggingPortABC:
    """Return a no-op logger respecting the logging port contract."""

    def _bound_logger(**_: Any) -> LoggingPortABC:
        return _create_noop_logger()

    return cast(
        LoggingPortABC,
        SimpleNamespace(
            info=lambda _msg, **__ctx: None,
            error=lambda _msg, **__ctx: None,
            debug=lambda _msg, **__ctx: None,
            warning=lambda _msg, **__ctx: None,
            apply_bind=_bound_logger,
        ),
    )


def _create_noop_output_writer() -> OutputWriterABC:
    """Return a deterministic no-op output writer."""

    def _write_result(
        df: Any,
        output_path: Path,
        entity_name: str,  # noqa: ARG001 - contract compatibility
        run_context: Any,  # noqa: ARG001 - contract compatibility
        *,
        column_order: list[str] | None = None,  # noqa: ARG001 - contract compatibility
    ) -> WriteResult:
        row_count = 0
        try:
            row_count = int(len(df))
        except Exception:
            row_count = 0
        path = Path(output_path)
        return WriteResult(
            path=path,
            row_count=row_count,
            duration_sec=0.0,
            checksum=None,
        )

    return cast(OutputWriterABC, SimpleNamespace(write_result=_write_result))


def _create_noop_record_source_factory() -> FileRecordSourceFactoryABC:
    """Return a record source factory producing empty in-memory sources."""

    return cast(
        FileRecordSourceFactoryABC,
        SimpleNamespace(
            create_csv_source=lambda **kwargs: InMemoryRecordSource(
                [], chunk_size=kwargs.get("chunk_size")
            ),
            create_id_list_source=lambda **kwargs: InMemoryRecordSource(
                [], chunk_size=kwargs.get("chunk_size")
            ),
        ),
    )


def _create_noop_metadata_builder() -> RunMetadataBuilderProtocol:
    """Return metadata builder that emits minimal deterministic payloads."""

    return cast(
        RunMetadataBuilderProtocol,
        SimpleNamespace(
            build_run_metadata=lambda context, write_result: {
                "run_id": getattr(context, "run_id", None),
                "row_count": getattr(write_result, "row_count", 0),
            },
            build_dry_run_metadata=lambda context, row_count: {
                "run_id": getattr(context, "run_id", None),
                "row_count": row_count,
            },
        ),
    )


def _create_noop_metrics_port() -> PipelineMetricsPortABC:
    """Return metrics port that records nothing (for tests)."""

    return cast(
        PipelineMetricsPortABC,
        SimpleNamespace(
            update_stage_duration=lambda **_kwargs: None,
            update_stage_total=lambda **_kwargs: None,
        ),
    )


def _create_noop_validator_factory() -> ValidatorFactoryABC:
    """Return validator factory that treats all data as valid (for tests)."""

    def _validate(df: Any) -> ValidationResult:
        return ValidationResult(is_valid=True, errors=[], warnings=[], validated_df=df)

    validator = SimpleNamespace(validate=_validate, is_valid=lambda _df: True)
    return cast(
        ValidatorFactoryABC,
        SimpleNamespace(create_validator=lambda _schema: validator),
    )


def build_pipeline_dependencies(
    config: PipelineConfig,
    *,
    logger: LoggingPortABC | None = None,
    output_writer: OutputWriterABC | None = None,
    validator_factory: ValidatorFactoryABC | None = None,
    record_source_factory: FileRecordSourceFactoryABC | None = None,
    metadata_builder: RunMetadataBuilderProtocol | None = None,
    metrics_port: PipelineMetricsPortABC | None = None,
    hooks: list[PipelineHookABC] | None = None,
    error_policy: ErrorPolicyABC | None = None,
    hash_service: HashServiceABC | None = None,
    post_transformer: TransformerABC | None = None,
    provider_registry: ProviderRegistryABC | None = None,
    provider_registry_provider: Callable[[], ProviderRegistryABC] | None = None,
    schema_provider: SchemaProviderABC | None = None,
) -> PipelineContainerABC:
    """Factory for the container."""
    return PipelineContainer(
        config,
        logger=logger,
        output_writer=output_writer,
        validator_factory=validator_factory,
        record_source_factory=record_source_factory,
        metadata_builder=metadata_builder,
        metrics_port=metrics_port,
        hooks=hooks,
        error_policy=error_policy,
        hash_service=hash_service,
        post_transformer=post_transformer,
        provider_registry=provider_registry,
        provider_registry_provider=provider_registry_provider,
        schema_provider=schema_provider,
    )
