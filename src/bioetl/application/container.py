"""
Dependency Injection Container for the application.

This module provides the core DI container that assembles pipeline dependencies.
The container follows the Composition Root pattern — all object graph construction
happens here, keeping the rest of the application free of "new" calls.

Architecture notes:
    - PipelineContainer implements PipelineContainerABC (contracts module)
    - Uses lazy initialization for factories to defer expensive operations
    - Supports both direct injection and provider callbacks for flexibility
    - Delegates specialized concerns to sub-factories (service, transform, runtime)

Dependency resolution order:
    1. Explicit constructor arguments (highest priority)
    2. Injected factory instances
    3. Default factory creation (lowest priority)

Example::

    container = PipelineContainer(
        config,
        loader=parquet_loader,
        provider_registry=registry,
    )
    logger = container.get_logger()
    hash_service = container.get_hash_service()
"""

from __future__ import annotations

from typing import Any, Callable

from bioetl.application.contracts import PipelineContainerABC
from bioetl.application.factories.noop import (
    create_noop_logger,
    create_noop_metadata_builder,
    create_noop_validator_factory,
)
from bioetl.application.factories.record_source import RecordSourceFactory
from bioetl.application.factories.runtime_factory import PipelineRuntimeFactory
from bioetl.application.factories.service_factory import (
    ApplicationServiceFactory,
    ApplicationServiceFactoryABC,
)
from bioetl.application.factories.transform_factory import (
    TransformComponentFactory,
    TransformComponentFactoryABC,
)
from bioetl.application.services.schema_bootstrap import (
    SchemaBootstrapService,
    create_schema_bootstrap_service,
)
from bioetl.domain.clients.base.output.contracts import RunMetadataBuilderProtocol
from bioetl.domain.configs import PipelineConfig
from bioetl.domain.observability import LoggingPortABC, MetricsPortABC
from bioetl.domain.pipelines.contracts import ErrorPolicyABC, LoaderABC, PipelineHookABC
from bioetl.domain.provider_registry import ProviderRegistryABC
from bioetl.domain.providers import ProviderDefinition, ProviderId
from bioetl.domain.record_source import RecordSourceABC
from bioetl.domain.transform.contracts import (
    HashServiceABC,
    IndexGeneratorABC,
    NormalizationServiceABC,
    TimestampProviderABC,
)
from bioetl.domain.transform.transformers import TransformerABC
from bioetl.domain.validation import SchemaProviderABC, ValidatorFactoryABC
from bioetl.domain.validation.service import ValidationService


class PipelineContainer(PipelineContainerABC):
    """DI Container for pipeline dependencies."""

    def __init__(
        self,
        config: PipelineConfig,
        *,
        service_factory: ApplicationServiceFactoryABC | None = None,
        transform_factory: TransformComponentFactoryABC | None = None,
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
        schema_bootstrap_service: SchemaBootstrapService | None = None,
    ) -> None:
        self._config = config
        self._provider_id = ProviderId(self._config.provider)

        # Resolve required dependencies
        if loader is None:
            raise ValueError("Loader must be provided.")
        self._loader = loader

        self._provider_registry, self._provider_registry_provider = (
            self._resolve_provider_registry(provider_registry, provider_registry_provider)
        )

        # Resolve optional dependencies with defaults
        self._validator_factory = validator_factory or create_noop_validator_factory()
        self._logger = logger or create_noop_logger()
        self._metadata_builder = metadata_builder or create_noop_metadata_builder()
        self._post_transformer = post_transformer

        # Schema bootstrap service (lazy registration on first validation service access)
        self._schema_bootstrap_service = (
            schema_bootstrap_service
            or create_schema_bootstrap_service(schema_provider=schema_provider)
        )

        # Initialize factories (lazy)
        self._injected_service_factory = service_factory
        self._injected_transform_factory = transform_factory
        self._service_factory: ApplicationServiceFactoryABC | None = None
        self._transform_factory: TransformComponentFactoryABC | None = None
        self._record_source_factory: RecordSourceFactory | None = None
        self._runtime_factory = PipelineRuntimeFactory(
            config, metrics_port, hooks, error_policy
        )

        # Store transform component overrides
        self._hash_service = hash_service
        self._index_generator = index_generator
        self._timestamp_provider = timestamp_provider

    @property
    def config(self) -> PipelineConfig:
        """Return the pipeline configuration."""
        return self._config

    # ─────────────────────────────────────────────────────────────────────────
    # Core Services
    # ─────────────────────────────────────────────────────────────────────────

    def get_logger(self) -> LoggingPortABC:
        """Return the logging port for pipeline observability."""
        return self._logger

    def get_validation_service(self) -> ValidationService:
        """Create and return a validation service with schema registry.

        Note:
            This triggers lazy schema registration on first call via
            SchemaBootstrapService.ensure_registered().
        """
        schema_provider = self._schema_bootstrap_service.ensure_registered()
        return ValidationService(
            schema_provider=schema_provider,
            validator_factory=self._validator_factory,
        )

    def get_loader(self) -> LoaderABC:
        """Return the loader for writing output data."""
        return self._loader

    def get_metadata_builder(self) -> RunMetadataBuilderProtocol:
        """Return the metadata builder for run result construction."""
        return self._metadata_builder

    # ─────────────────────────────────────────────────────────────────────────
    # Application Services (via ServiceFactory)
    # ─────────────────────────────────────────────────────────────────────────

    def get_extraction_service(self) -> Any:
        """Create and return an extraction service via the service factory."""
        return self._get_service_factory().create_extraction_service()

    def get_normalization_service(self) -> NormalizationServiceABC:
        """Create and return a normalization service via the service factory."""
        return self._get_service_factory().create_normalization_service()

    def get_entity_model_registry(self) -> Any:
        """Create and return an entity model registry via the service factory."""
        return self._get_service_factory().create_entity_model_registry()

    # ─────────────────────────────────────────────────────────────────────────
    # Transform Components (via TransformFactory)
    # ─────────────────────────────────────────────────────────────────────────

    def get_hash_service(self) -> HashServiceABC:
        """Return the hash service for record deduplication."""
        return self._get_transform_factory().get_hash_service()

    def get_index_generator(self) -> IndexGeneratorABC:
        """Return the index generator for unique record identifiers."""
        return self._get_transform_factory().get_index_generator()

    def get_timestamp_provider(self) -> TimestampProviderABC:
        """Return the timestamp provider for record timestamping."""
        return self._get_transform_factory().get_timestamp_provider()

    def get_post_transformer(
        self, *, version_provider: Callable[[], str | None] | None = None
    ) -> TransformerABC:
        """
        Return the post-transformer for adding standard fields.

        The post-transformer adds hash, index, and timestamp columns to records.

        Args:
            version_provider: Optional callable returning source version string.
        """
        if self._post_transformer is not None:
            return self._post_transformer
        return self._get_transform_factory().get_post_transformer(
            version_provider=version_provider
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Record Source (via RecordSourceFactory)
    # ─────────────────────────────────────────────────────────────────────────

    def get_record_source(
        self,
        extraction_service: Any,
        *,
        limit: int | None = None,
        logger: LoggingPortABC | None = None,
        model_cls: type | None = None,
        batch_adapter: Any | None = None,
    ) -> RecordSourceABC:
        """
        Create a record source for iterating over extracted data.

        Record sources return raw dicts. Domain model conversion should happen
        via RecordMapperABC in ExtractStage.

        Args:
            extraction_service: Service providing raw data extraction.
            limit: Optional maximum number of records to extract.
            logger: Logger instance (defaults to container's logger).
            model_cls: Deprecated. Use RecordMapperABC for domain model conversion.
            batch_adapter: Optional adapter for batch processing.

        Returns:
            Record source providing chunked data iteration (raw dicts).
        """
        return self._get_record_source_factory().create_record_source(
            extraction_service,
            limit=limit,
            logger=logger or self.get_logger(),
            model_cls=model_cls,  # Deprecated, triggers warning if not None
            batch_adapter=batch_adapter,
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Runtime Components (via RuntimeFactory)
    # ─────────────────────────────────────────────────────────────────────────

    def get_hooks(self) -> list[PipelineHookABC]:
        """Return the list of pipeline execution hooks."""
        return self._runtime_factory.get_hooks(self.get_logger())

    def get_error_policy(self) -> ErrorPolicyABC:
        """Return the error handling policy for pipeline stages."""
        return self._runtime_factory.get_error_policy()

    # ─────────────────────────────────────────────────────────────────────────
    # Private Factory Accessors
    # ─────────────────────────────────────────────────────────────────────────

    def _get_service_factory(self) -> ApplicationServiceFactoryABC:
        if self._service_factory is None:
            if self._injected_service_factory is not None:
                self._service_factory = self._injected_service_factory
            else:
                self._service_factory = ApplicationServiceFactory(
                    self._config,
                    self._get_provider_registry(),
                    logger=self._logger,
                    metrics=self._runtime_factory.get_metrics_port(),
                )
        return self._service_factory

    def _get_transform_factory(self) -> TransformComponentFactoryABC:
        if self._transform_factory is None:
            if self._injected_transform_factory is not None:
                self._transform_factory = self._injected_transform_factory
            else:
                self._transform_factory = TransformComponentFactory(
                    self._config,
                    hash_service=self._hash_service,
                    index_generator=self._index_generator,
                    timestamp_provider=self._timestamp_provider,
                )
        return self._transform_factory

    def _get_record_source_factory(self) -> RecordSourceFactory:
        if self._record_source_factory is None:
            self._record_source_factory = RecordSourceFactory(
                self._config,
                self._get_provider_definition(),
                self._resolve_provider_config,
            )
        return self._record_source_factory

    def _get_provider_registry(self) -> ProviderRegistryABC:
        if self._provider_registry is not None:
            return self._provider_registry
        if self._provider_registry_provider is None:
            raise RuntimeError("Provider registry provider is not configured")
        self._provider_registry = self._provider_registry_provider()
        if self._provider_registry is None:
            raise RuntimeError("Provider registry provider returned None")
        return self._provider_registry

    def _get_provider_definition(self) -> ProviderDefinition:
        return self._get_provider_registry().get_provider(self._provider_id)

    def _resolve_provider_config(self, definition: ProviderDefinition) -> Any:
        source_config = self._config.get_source_config(self._provider_id.value)
        if not isinstance(source_config, definition.config_type):
            raise TypeError(
                f"Expected config type {definition.config_type.__name__} for "
                f"provider '{self._provider_id.value}'"
            )
        return source_config

    @staticmethod
    def _resolve_provider_registry(
        registry: ProviderRegistryABC | None,
        provider: Callable[[], ProviderRegistryABC] | None,
    ) -> tuple[ProviderRegistryABC | None, Callable[[], ProviderRegistryABC] | None]:
        if registry is None and provider is None:
            raise ValueError(
                "Provider registry must be supplied (instance or provider callable)"
            )
        return registry, provider


def create_default_container_factory() -> Callable[..., PipelineContainerABC]:
    """Return the default container factory."""
    return PipelineContainer
