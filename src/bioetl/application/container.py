"""Dependency Injection Container for the application."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, Callable, cast

from bioetl.application.factories.hooks import PipelineHookFactory
from bioetl.application.factories.noop import create_noop_metrics_port
from bioetl.application.factories.record_source import RecordSourceFactory
from bioetl.application.factories.services import ProviderServiceFactory
from bioetl.application.mappers.chembl.record_mapper import ChemblRecordMapper
from bioetl.application.mappers.contracts import RecordMapperABC
from bioetl.application.pipelines.contracts import PipelineContainerABC
from bioetl.application.pipelines.hooks_impl import FailFastErrorPolicyImpl
from bioetl.application.services.schema_bootstrap import (
    SchemaBootstrapService,
    create_schema_bootstrap_service,
)
from bioetl.application.services.schema_contract_provider import (
    SchemaContractProviderImpl,
)
from bioetl.domain.clients.base.output.contracts import (
    RunMetadataBuilderProtocol,
)
from bioetl.domain.configs import PipelineConfig
from bioetl.domain.observability import LoggingPortABC, MetricsPortABC
from bioetl.domain.pipelines.contracts import ErrorPolicyABC, LoaderABC, PipelineHookABC
from bioetl.domain.ports.parsing import ResponseParserPortABC
from bioetl.domain.ports.schema import SchemaContractProviderABC
from bioetl.domain.provider_registry import ProviderRegistryABC
from bioetl.domain.providers import ProviderDefinition, ProviderId
from bioetl.domain.record_source import RecordSourceABC
from bioetl.domain.schemas import register_schemas
from bioetl.domain.schemas.registry import SchemaRegistry
from bioetl.domain.transform.contracts import (
    HashServiceABC,
    IndexGeneratorABC,
    NormalizationServiceABC,
    TimestampProviderABC,
)
from bioetl.domain.transform.factories import default_post_transformer
from bioetl.domain.transform.transformers import TransformerABC
from bioetl.domain.validation import SchemaProviderABC, ValidatorFactoryABC
from bioetl.domain.validation.contracts import ValidationResult
from bioetl.domain.validation.service import ValidationService
from bioetl.infrastructure.clients.chembl.response_parser import (
    ChemblGenericResponseParser,
)


class PipelineContainer(PipelineContainerABC):
    """
    DI Container for pipeline dependencies.
    """

    def __init__(
        self,
        config: PipelineConfig,
        *,
        logger: LoggingPortABC | None = None,
        loader: LoaderABC | None = None,
        validator_factory: ValidatorFactoryABC | None = None,
        metadata_builder: RunMetadataBuilderProtocol | None = None,
        metrics_port: MetricsPortABC | None = None,
        hooks: list[PipelineHookABC] | None = None,
        error_policy: ErrorPolicyABC | None = None,
        hash_service: HashServiceABC | None = None,
        index_generator: IndexGeneratorABC | None = None,
        timestamp_provider: TimestampProviderABC | None = None,
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
        self._index_generator = index_generator
        self._timestamp_provider = timestamp_provider
        self._post_transformer = post_transformer
        self._metadata_builder = self._resolve_metadata_builder(metadata_builder)
        self._metrics_port = self._resolve_metrics_port(metrics_port)
        self._provider_registry, self._provider_registry_provider = (
            self._resolve_provider_registry(
                provider_registry, provider_registry_provider
            )
        )
        if loader is None:
            raise ValueError("Loader must be provided.")
        self._loader = loader
        register_schemas(self._schema_provider)

        # Initialize factory helpers
        self._service_factory: ProviderServiceFactory | None = None
        self._record_source_factory: RecordSourceFactory | None = None
        self._hook_factory: PipelineHookFactory | None = None

    def _get_service_factory(self) -> ProviderServiceFactory:
        if self._service_factory is None:
            self._service_factory = ProviderServiceFactory(
                self._config,
                self._get_provider_definition(),
                self._resolve_provider_config,
            )
        return self._service_factory

    def _get_record_source_factory(self) -> RecordSourceFactory:
        if self._record_source_factory is None:
            self._record_source_factory = RecordSourceFactory(
                self._config,
                self._get_provider_definition(),
                self._resolve_provider_config,
            )
        return self._record_source_factory

    def _get_hook_factory(self) -> PipelineHookFactory:
        if self._hook_factory is None:
            self._hook_factory = PipelineHookFactory(
                self._config,
                self._metrics_port,
            )
        return self._hook_factory

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

    def _resolve_metadata_builder(
        self, metadata_builder: RunMetadataBuilderProtocol | None
    ) -> RunMetadataBuilderProtocol:
        return metadata_builder or _create_noop_metadata_builder()

    def _resolve_metrics_port(
        self, metrics_port: MetricsPortABC | None
    ) -> MetricsPortABC:
        return metrics_port or create_noop_metrics_port()

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

    def get_loader(self) -> LoaderABC:
        """Get the loader component."""
        return self._loader

    def get_metadata_builder(self) -> RunMetadataBuilderProtocol:
        """Get metadata builder port."""
        return self._metadata_builder

    def get_normalization_service(self) -> NormalizationServiceABC:
        """Create normalization service for the configured provider."""
        return self._get_service_factory().create_normalization_service()

    def get_record_source(
        self,
        extraction_service: Any,
        *,
        limit: int | None = None,
        logger: LoggingPortABC | None = None,
        model_cls: type | None = None,
        batch_adapter: Any | None = None,
    ) -> RecordSourceABC:
        """Create record source based on pipeline input configuration."""
        return self._get_record_source_factory().create_record_source(
            extraction_service,
            limit=limit,
            logger=logger or self.get_logger(),
            model_cls=model_cls,
            batch_adapter=batch_adapter,
        )

    def get_extraction_service(self) -> Any:
        """Get the extraction service based on provider configuration."""
        return self._get_service_factory().create_extraction_service()

    def get_hash_service(self) -> HashServiceABC:
        """Get the hash service.

        The concrete implementation must be injected from outer layers
        (e.g. interfaces wiring or tests) to avoid application →
        infrastructure dependencies.
        """
        if self._hash_service is None:
            raise RuntimeError("Hash service is not configured for this container")
        return self._hash_service

    def get_index_generator(self) -> IndexGeneratorABC:
        """Get the index generator.

        The concrete implementation must be injected from outer layers
        (e.g. interfaces wiring or tests) to avoid application →
        infrastructure dependencies.
        """
        if self._index_generator is None:
            raise RuntimeError("Index generator is not configured for this container")
        return self._index_generator

    def get_timestamp_provider(self) -> TimestampProviderABC:
        """Get the timestamp provider.

        The concrete implementation must be injected from outer layers
        (e.g. interfaces wiring or tests) to avoid application →
        infrastructure dependencies.
        """
        if self._timestamp_provider is None:
            raise RuntimeError(
                "Timestamp provider is not configured for this container"
            )
        return self._timestamp_provider

    def get_post_transformer(
        self, *, version_provider: Callable[[], str] | None = None
    ) -> TransformerABC:
        """Собирает цепочку стандартных трансформеров."""
        if self._post_transformer is None:
            self._post_transformer = default_post_transformer(
                hash_service=self.get_hash_service(),
                index_generator=self.get_index_generator(),
                timestamp_provider=self.get_timestamp_provider(),
                business_key_fields=self._config.quality.hashing.business_key_fields,
                version_provider=version_provider,
            )
        return self._post_transformer

    def get_hooks(self) -> list[PipelineHookABC]:
        """Возвращает список хуков выполнения пайплайна."""
        if self._hooks is None:
            self._hooks = self._get_hook_factory().create_hooks(self.get_logger())
        return list(self._hooks)

    def get_error_policy(self) -> ErrorPolicyABC:
        """Возвращает политику обработки ошибок пайплайна."""
        if self._error_policy is None:
            self._error_policy = FailFastErrorPolicyImpl()
        return self._error_policy

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


def _create_noop_validator_factory() -> ValidatorFactoryABC:
    """Return validator factory that treats all data as valid (for tests)."""

    def _validate(df: Any) -> ValidationResult:
        return ValidationResult(is_valid=True, errors=[], warnings=[], validated_df=df)

    validator = SimpleNamespace(validate=_validate, is_valid=lambda _df: True)
    return cast(
        ValidatorFactoryABC,
        SimpleNamespace(create_validator=lambda _schema: validator),
    )


def create_default_container_factory() -> Callable[..., PipelineContainerABC]:
    """Return the default container factory."""
    return PipelineContainer


class SimplePipelineContainer:
    """Simplified container for pipeline dependencies.

    This container provides a streamlined approach to dependency injection
    for the new architecture. It focuses on:
    - SchemaBootstrapService for schema initialization
    - SchemaContractProvider for schema metadata access
    - RecordMapper for record transformation
    - ResponseParser for API response parsing

    Example:
        >>> container = SimplePipelineContainer()
        >>> container.bootstrap()
        >>> mapper = container.record_mapper
        >>> parser = container.response_parser
    """

    def __init__(self) -> None:
        """Initialize the container with lazy-initialized components."""
        self._schema_bootstrap: SchemaBootstrapService | None = None
        self._schema_contract_provider: SchemaContractProviderABC | None = None
        self._record_mapper: RecordMapperABC | None = None
        self._response_parser: ResponseParserPortABC | None = None
        self._bootstrapped: bool = False

    def bootstrap(self) -> None:
        """Initialize all application services.

        This method must be called before accessing container properties.
        It initializes the schema bootstrap service, registers schemas,
        and sets up the schema contract provider.

        Raises:
            RuntimeError: If bootstrap fails during initialization.
        """
        if self._bootstrapped:
            return

        # 1. Schema bootstrap
        self._schema_bootstrap = create_schema_bootstrap_service()
        schema_provider = self._schema_bootstrap.ensure_registered()

        # 2. Schema contract provider
        self._schema_contract_provider = SchemaContractProviderImpl(schema_provider)

        # 3. Inject into infrastructure
        from bioetl.infrastructure.config.loader import set_schema_contract_provider

        set_schema_contract_provider(self._schema_contract_provider)

        self._bootstrapped = True

    @property
    def is_bootstrapped(self) -> bool:
        """Check if the container has been bootstrapped."""
        return self._bootstrapped

    @property
    def record_mapper(self) -> RecordMapperABC:
        """Get record mapper (lazy init).

        Returns:
            ChemblRecordMapper instance for mapping raw records to domain models.

        Note:
            This property uses lazy initialization and does not require
            bootstrap() to be called first.
        """
        if self._record_mapper is None:
            self._record_mapper = ChemblRecordMapper()
        return self._record_mapper

    @property
    def response_parser(self) -> ResponseParserPortABC:
        """Get generic response parser.

        Returns:
            ChemblGenericResponseParser instance for parsing API responses.

        Note:
            This property uses lazy initialization and does not require
            bootstrap() to be called first.
        """
        if self._response_parser is None:
            self._response_parser = ChemblGenericResponseParser()
        return self._response_parser

    @property
    def schema_contract_provider(self) -> SchemaContractProviderABC:
        """Get schema contract provider.

        Returns:
            Configured SchemaContractProviderImpl instance.

        Raises:
            RuntimeError: If container has not been bootstrapped.
        """
        if self._schema_contract_provider is None:
            raise RuntimeError("Container not bootstrapped")
        return self._schema_contract_provider

    @property
    def schema_bootstrap(self) -> SchemaBootstrapService:
        """Get schema bootstrap service.

        Returns:
            Configured SchemaBootstrapService instance.

        Raises:
            RuntimeError: If container has not been bootstrapped.
        """
        if self._schema_bootstrap is None:
            raise RuntimeError("Container not bootstrapped")
        return self._schema_bootstrap

    def reset(self) -> None:
        """Reset the container state (primarily for testing).

        Clears all cached instances and resets bootstrap state.
        """
        from bioetl.infrastructure.config.loader import clear_schema_contract_provider

        clear_schema_contract_provider()

        self._schema_bootstrap = None
        self._schema_contract_provider = None
        self._record_mapper = None
        self._response_parser = None
        self._bootstrapped = False
