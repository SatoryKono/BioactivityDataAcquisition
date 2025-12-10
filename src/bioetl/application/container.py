"""Dependency Injection Container for the application."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, Callable, cast

from bioetl.application.factories.hooks import PipelineHookFactory
from bioetl.application.factories.noop import create_noop_metrics_port
from bioetl.application.factories.record_source import RecordSourceFactory
from bioetl.application.factories.services import ProviderServiceFactory
from bioetl.application.pipelines.contracts import LoaderABC, PipelineContainerABC
from bioetl.application.pipelines.hooks_impl import FailFastErrorPolicyImpl
from bioetl.domain.clients.base.output.contracts import (
    RunMetadataBuilderProtocol,
)
from bioetl.domain.configs import PipelineConfig
from bioetl.domain.observability import LoggingPortABC, MetricsPortABC
from bioetl.domain.pipelines.contracts import ErrorPolicyABC, PipelineHookABC
from bioetl.domain.provider_registry import ProviderRegistryABC
from bioetl.domain.providers import ProviderDefinition, ProviderId
from bioetl.domain.record_source import RecordSourceABC
from bioetl.domain.schemas import register_schemas
from bioetl.domain.schemas.registry import SchemaRegistry
from bioetl.domain.transform.contracts import HashServiceABC, NormalizationServiceABC
from bioetl.domain.transform.factories import default_post_transformer
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
        loader: LoaderABC | None = None,
        validator_factory: ValidatorFactoryABC | None = None,
        metadata_builder: RunMetadataBuilderProtocol | None = None,
        metrics_port: MetricsPortABC | None = None,
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
