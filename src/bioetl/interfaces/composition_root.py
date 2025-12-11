"""
Composition Root for assembling the application's dependency graph.

This module is the single place where concrete implementations are instantiated
and wired together. No other module should create dependencies with default fallbacks.

Usage:
    # For production:
    root = CompositionRoot()
    container = root.create_pipeline_container(config)
    config_loader = root.create_config_loader()

    # For testing with custom observability (recommended):
    from bioetl.interfaces.factories import ObservabilityFactoryABC

    class MockObservabilityFactory(ObservabilityFactoryABC):
        def create_logger(self) -> LoggingPortABC:
            return mock_logger
        def create_metrics(self) -> MetricsPortABC:
            return mock_metrics

    root = CompositionRoot(
        observability_factory=MockObservabilityFactory(),
        schema_contract_provider=mock_provider,
    )

    # Legacy usage (deprecated - will be removed in future release):
    # Use create_composition_root_with_legacy() for backward compatibility
    from bioetl.interfaces.legacy_adapters import create_composition_root_with_legacy
    root = create_composition_root_with_legacy(
        logger=mock_logger,
        metrics=mock_metrics,
    )
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable

import requests

from bioetl.application.container import PipelineContainer
from bioetl.application.contracts import PipelineContainerABC
from bioetl.application.services.config_migration_service import (
    ConfigMigrationService,
    ConfigMigrationServiceProtocol,
)
from bioetl.domain.clients.base.contracts import RateLimiterABC
from bioetl.domain.configs import HttpClientConfig, PipelineConfig
from bioetl.domain.configs.contracts import PipelineConfigLoaderProtocol
from bioetl.domain.observability import LoggingPortABC, MetricsPortABC
from bioetl.domain.ports.schema import SchemaContractProviderABC
from bioetl.domain.provider_registry import ProviderRegistryABC
from bioetl.infrastructure.clients.base.factories import build_http_client
from bioetl.interfaces.factories import (
    DefaultInfrastructureFactory,
    DefaultObservabilityFactory,
    InfrastructureFactoryABC,
    ObservabilityFactoryABC,
)

if TYPE_CHECKING:
    from bioetl.application.config.resolution import ConfigPathResolver
    from bioetl.infrastructure.config.loader import SchemaContractLoader


@dataclass(frozen=True)
class ObservabilityStack:
    """Container for observability dependencies."""

    logger: LoggingPortABC
    metrics: MetricsPortABC


class CompositionRoot:
    """Single dependency assembly point for interfaces layer.

    All concrete implementations are created here. Other modules
    obtain dependencies through this class, not directly.

    Example:
        # Production
        root = CompositionRoot()
        container = root.create_pipeline_container(config)

        # Testing with custom factory (recommended)
        root = CompositionRoot(observability_factory=MockObservabilityFactory())
        container = root.create_pipeline_container(config)
    """

    def __init__(
        self,
        *,
        observability_factory: ObservabilityFactoryABC | None = None,
        infrastructure_factory: InfrastructureFactoryABC | None = None,
        http_session_factory: type | None = None,
        schema_contract_provider: SchemaContractProviderABC | None = None,
    ) -> None:
        """
        Initialize composition root with optional overrides.

        Args:
            observability_factory: Factory for observability components
                (defaults to DefaultObservabilityFactory)
            infrastructure_factory: Factory for infrastructure components
                (defaults to DefaultInfrastructureFactory)
            http_session_factory: HTTP session factory class
            schema_contract_provider: Custom schema contract provider
                (defaults to bootstrapped provider from schema registry)
        """
        # Factories
        self._observability = observability_factory or DefaultObservabilityFactory()
        self._infrastructure = infrastructure_factory or DefaultInfrastructureFactory()

        self._http_session_factory = http_session_factory or requests.Session
        self._schema_contract_provider = schema_contract_provider

        # Lazy-loaded provider registry
        self._provider_registry: ProviderRegistryABC | None = None

    # =========================================================================
    # Provider Registry
    # =========================================================================

    def get_provider_registry(self) -> ProviderRegistryABC:
        """Get or create the provider registry instance.

        This method creates and bootstraps the provider registry lazily.
        The registry is cached for subsequent calls.

        This is the preferred method for obtaining a provider registry,
        replacing the deprecated global get_provider_registry() function.

        Returns:
            Configured ProviderRegistryABC instance.

        Example:
            >>> root = CompositionRoot()
            >>> registry = root.get_provider_registry()
            >>> provider = registry.get_provider(ProviderId("chembl"))
        """
        if self._provider_registry is None:
            from bioetl.infrastructure.config.provider_registry import (
                ProviderRegistryLoader,
            )
            from bioetl.infrastructure.provider_registry import (
                InMemoryProviderRegistry,
            )

            self._provider_registry = InMemoryProviderRegistry()
            loader = ProviderRegistryLoader()
            loader.get_providers(registry=self._provider_registry)

        return self._provider_registry

    # =========================================================================
    # Observability
    # =========================================================================

    def get_logger(self) -> LoggingPortABC:
        """Get or create the logger instance."""
        return self._observability.create_logger()

    def get_metrics(self) -> MetricsPortABC:
        """Get or create the metrics instance."""
        return self._observability.create_metrics()

    def get_observability_stack(self) -> ObservabilityStack:
        """Get the complete observability stack."""
        return ObservabilityStack(
            logger=self.get_logger(),
            metrics=self.get_metrics(),
        )

    # =========================================================================
    # HTTP Infrastructure
    # =========================================================================

    def create_http_session(self) -> Any:
        """Create a new HTTP session."""
        return self._http_session_factory()

    def create_http_transport(
        self,
        provider: str,
        config: HttpClientConfig,
        *,
        base_client: Any | None = None,
    ) -> Any:
        """
        Create an HTTP transport with all dependencies injected.

        Args:
            provider: Provider identifier (e.g., "chembl")
            config: HTTP client configuration
            base_client: Optional pre-configured HTTP client

        Returns:
            Fully configured HTTP transport instance
        """
        return build_http_client(
            provider=provider,
            logger=self.get_logger(),
            metrics=self.get_metrics(),
            config=config,
            base_client=base_client or self.create_http_session(),
        )

    def create_rate_limiter(
        self,
        rate: float,
        capacity: float | None = None,
    ) -> RateLimiterABC:
        """
        Create a rate limiter with all dependencies injected.

        Args:
            rate: Tokens per second
            capacity: Maximum bucket capacity (defaults to rate)

        Returns:
            Configured rate limiter instance
        """
        return self._infrastructure.create_rate_limiter(
            logger=self.get_logger(),
            rate=rate,
            capacity=capacity,
        )

    # =========================================================================
    # Schema Contract Provider
    # =========================================================================

    def get_schema_contract_provider(self) -> SchemaContractProviderABC:
        """Get or create the schema contract provider instance.

        If not provided during initialization, creates a default provider
        by bootstrapping the schema registry.

        Returns:
            Configured SchemaContractProviderABC instance.
        """
        if self._schema_contract_provider is None:
            self._schema_contract_provider = _create_default_schema_contract_provider()
        return self._schema_contract_provider

    def create_schema_contract_loader(self) -> "SchemaContractLoader":
        """Create a SchemaContractLoader with the configured provider.

        This is the preferred method for obtaining a configuration loader
        with proper dependency injection.

        Returns:
            SchemaContractLoader with injected schema contract provider.

        Example:
            >>> root = CompositionRoot()
            >>> loader = root.create_schema_contract_loader()
            >>> config = loader.get_pipeline_config("chembl.activity")
        """
        from bioetl.infrastructure.config.loader import SchemaContractLoader

        return SchemaContractLoader(self.get_schema_contract_provider())

    # =========================================================================
    # Config Migration Service
    # =========================================================================

    def create_config_migration_service(self) -> ConfigMigrationServiceProtocol:
        """Create a ConfigMigrationService for migrating legacy configs.

        The ConfigMigrationService orchestrates migration of legacy pipeline
        configuration formats to the current structure. It delegates actual
        migration logic to the infrastructure layer (ConfigMigrator) while
        keeping the domain layer (PipelineConfig) clean.

        This follows Hexagonal Architecture principles:
        - Domain layer (PipelineConfig) contains only business rules
        - Application layer (ConfigMigrationService) orchestrates use cases
        - Infrastructure layer (ConfigMigrator) handles technical migration
        - Interfaces layer (CompositionRoot) wires them together

        Returns:
            ConfigMigrationServiceProtocol: Service for migrating and validating
                raw config dictionaries into PipelineConfig domain objects.

        Example:
            >>> root = CompositionRoot()
            >>> migration_service = root.create_config_migration_service()
            >>> raw_config = {"entity": "activity", "provider": "chembl", ...}
            >>> config = migration_service.migrate_and_validate(raw_config)
        """
        from bioetl.infrastructure.config.migration import ConfigMigrator

        return ConfigMigrationService(migrator=ConfigMigrator)

    # =========================================================================
    # Pipeline Infrastructure
    # =========================================================================

    def create_pipeline_container(
        self,
        config: PipelineConfig,
        *,
        provider_registry: ProviderRegistryABC | None = None,
        provider_registry_provider: Callable[[], ProviderRegistryABC] | None = None,
    ) -> PipelineContainerABC:
        """Assemble pipeline container with all infrastructure dependencies.

        Args:
            config: Pipeline configuration
            provider_registry: Pre-built registry (optional)
            provider_registry_provider: Factory for registry (optional)

        Returns:
            Fully configured PipelineContainer
        """
        from bioetl.infrastructure.clients.base.abc_registry_resolver import (
            ABCRegistryResolver,
        )

        # Create resolver with both infrastructure and application YAML files
        application_impls_path = Path(__file__).parent / "abc_impls_application.yaml"
        resolver = ABCRegistryResolver(
            additional_impls_paths=[application_impls_path]
        )

        # Resolve factories from registry
        loader_factory = resolver.resolve_default_factory("LoaderABC")
        frame_converter_factory = resolver.resolve_default_factory(
            "OutputFrameConverterABC"
        )
        hash_service_factory = resolver.resolve_default_factory("HashServiceABC")
        timestamp_provider_factory = resolver.resolve_default_factory(
            "TimestampProviderABC"
        )
        index_generator_factory = resolver.resolve_default_factory("IndexGeneratorABC")

        # Create components
        metrics_port = self.get_metrics()
        converter_id = getattr(config.sink.output, "converter", None)
        frame_converter = frame_converter_factory(converter_id)

        loader = loader_factory(
            config=config.quality.determinism,
            qc_config=config.quality.qc,
            metrics_port=metrics_port,
            converter=frame_converter,
        )

        from bioetl.application.services.schema_bootstrap import (
            create_schema_bootstrap_service,
        )
        from bioetl.infrastructure.validation.bootstrap import register_schemas

        schema_bootstrap = create_schema_bootstrap_service(register_fn=register_schemas)

        return PipelineContainer(
            config,
            logger=self.get_logger(),
            loader=loader,
            validator_factory=self._infrastructure.create_validator_factory(),
            metadata_builder=self._infrastructure.create_metadata_builder(),
            metrics_port=metrics_port,
            hash_service=hash_service_factory(),
            timestamp_provider=timestamp_provider_factory(),
            index_generator=index_generator_factory(),
            provider_registry=provider_registry,
            provider_registry_provider=provider_registry_provider,
            schema_bootstrap_service=schema_bootstrap,
        )

    def create_config_loader(self) -> PipelineConfigLoaderProtocol:
        """Create config loader port backed by infrastructure loader.

        Returns:
            PipelineConfigLoaderProtocol: Config loader with bound schema provider.
        """
        return self._infrastructure.create_config_loader()

    def create_config_path_resolver(
        self,
        configs_root: Path | str | None = None,
    ) -> "ConfigPathResolver":
        """Create ConfigPathResolver with default or specified configs root.

        Args:
            configs_root: Root directory for configs. If None, uses infrastructure
                default (BIOETL_CONFIG_DIR env var or 'configs' directory).

        Returns:
            ConfigPathResolver instance.
        """
        from bioetl.application.config.resolution import ConfigPathResolver
        from bioetl.infrastructure.config.sources import get_configs_root

        effective_root = (
            Path(configs_root) if configs_root is not None else get_configs_root(None)
        )
        return ConfigPathResolver(effective_root)


def _create_default_schema_contract_provider() -> SchemaContractProviderABC:
    """Create default schema contract provider by bootstrapping schema registry.

    This function is called lazily when no provider is explicitly configured.

    Returns:
        Configured SchemaContractProviderImpl instance.
    """
    from bioetl.application.services.schema_bootstrap import (
        create_schema_bootstrap_service,
    )
    from bioetl.application.services.schema_contract_provider import (
        SchemaContractProviderImpl,
    )
    from bioetl.infrastructure.validation.bootstrap import register_schemas

    schema_service = create_schema_bootstrap_service(register_fn=register_schemas)
    schema_provider = schema_service.ensure_registered()
    return SchemaContractProviderImpl(schema_provider)


# =============================================================================
# Module-level singleton
# =============================================================================

_default_root: CompositionRoot | None = None


def get_composition_root() -> CompositionRoot:
    """
    Get the default composition root singleton.

    For testing, create a new CompositionRoot with mock dependencies instead.
    """
    global _default_root
    if _default_root is None:
        _default_root = CompositionRoot()
    return _default_root


def reset_composition_root() -> None:
    """Reset the default composition root (useful for tests)."""
    global _default_root
    _default_root = None


# =============================================================================
# Module-level convenience functions (backward compatible API)
# =============================================================================


def build_default_container(
    config: PipelineConfig,
    *,
    provider_registry: ProviderRegistryABC | None = None,
    provider_registry_provider: Callable[[], ProviderRegistryABC] | None = None,
) -> PipelineContainerABC:
    """Construct application container with infrastructure defaults.

    This is a convenience wrapper around CompositionRoot.create_pipeline_container()
    that uses the default singleton.

    Args:
        config: Pipeline configuration
        provider_registry: Pre-built registry (optional)
        provider_registry_provider: Factory for registry (optional)

    Returns:
        Fully configured PipelineContainer
    """
    return get_composition_root().create_pipeline_container(
        config,
        provider_registry=provider_registry,
        provider_registry_provider=provider_registry_provider,
    )


def create_config_loader() -> PipelineConfigLoaderProtocol:
    """Return config loader port backed by infrastructure loader.

    This is a convenience wrapper around CompositionRoot.create_config_loader()
    that uses the default singleton.

    Returns:
        PipelineConfigLoaderProtocol: Config loader with bound schema provider.
    """
    return get_composition_root().create_config_loader()


def create_config_path_resolver(
    configs_root: Path | str | None = None,
) -> "ConfigPathResolver":
    """Create ConfigPathResolver with default or specified configs root.

    This is a convenience wrapper around CompositionRoot.create_config_path_resolver()
    that uses the default singleton.

    Args:
        configs_root: Root directory for configs. If None, uses infrastructure
            default (BIOETL_CONFIG_DIR env var or 'configs' directory).

    Returns:
        ConfigPathResolver instance.
    """
    return get_composition_root().create_config_path_resolver(configs_root)


def create_config_migration_service() -> ConfigMigrationServiceProtocol:
    """Create ConfigMigrationService for migrating legacy configs.

    This is a convenience wrapper around
    CompositionRoot.create_config_migration_service()
    that uses the default singleton.

    The service orchestrates migration of legacy pipeline configuration formats
    to the current structure, delegating to infrastructure layer (ConfigMigrator)
    while keeping domain layer (PipelineConfig) clean.

    Returns:
        ConfigMigrationServiceProtocol: Service for migrating and validating
            raw config dictionaries into PipelineConfig domain objects.

    Example:
        >>> from bioetl.interfaces.composition_root import (
        ...     create_config_migration_service,
        ... )
        >>> service = create_config_migration_service()
        >>> raw = {"entity": "activity", "provider": "chembl", ...}
        >>> config = service.migrate_and_validate(raw)
    """
    return get_composition_root().create_config_migration_service()


__all__ = [
    "CompositionRoot",
    "ConfigMigrationServiceProtocol",
    "ObservabilityStack",
    "build_default_container",
    "create_config_loader",
    "create_config_migration_service",
    "create_config_path_resolver",
    "get_composition_root",
    "reset_composition_root",
]
