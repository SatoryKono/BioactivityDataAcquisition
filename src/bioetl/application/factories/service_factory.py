"""
Application-level service factory.

Provides a facade for creating extraction and normalization services,
abstracting away provider-specific details from the container.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from bioetl.application.factories.services import ProviderServiceFactory
from bioetl.domain.configs import PipelineConfig
from bioetl.domain.observability.contracts import LoggingPortABC, MetricsPortABC
from bioetl.domain.provider_registry import ProviderRegistryABC
from bioetl.domain.providers import ProviderDefinition, ProviderId
from bioetl.domain.transform.contracts import NormalizationServiceABC


class ApplicationServiceFactoryABC(ABC):
    """Abstract base for application service factories."""

    @abstractmethod
    def create_extraction_service(self) -> Any:
        """Create extraction service for the configured provider."""

    @abstractmethod
    def create_normalization_service(self) -> NormalizationServiceABC:
        """Create normalization service for the configured provider."""


class ApplicationServiceFactory(ApplicationServiceFactoryABC):
    """
    Factory for creating application-level services.

    Encapsulates provider resolution and service creation logic,
    delegating to ProviderServiceFactory for actual service instantiation.
    """

    def __init__(
        self,
        config: PipelineConfig,
        provider_registry: ProviderRegistryABC,
        *,
        logger: LoggingPortABC | None = None,
        metrics: MetricsPortABC | None = None,
    ) -> None:
        """
        Initialize the application service factory.

        Args:
            config: Pipeline configuration.
            provider_registry: Registry for looking up provider definitions.
            logger: Optional logging port for service creation.
            metrics: Optional metrics port for service creation.
        """
        self._config = config
        self._provider_registry = provider_registry
        self._logger = logger
        self._metrics = metrics
        self._provider_id = ProviderId(config.provider)
        self._provider_factory: ProviderServiceFactory | None = None

    def _get_provider_definition(self) -> ProviderDefinition:
        """Get provider definition from registry."""
        return self._provider_registry.get_provider(self._provider_id)

    def _resolve_provider_config(self, definition: ProviderDefinition) -> Any:
        """Resolve and validate provider-specific configuration."""
        source_config = self._config.get_source_config(self._provider_id.value)
        if not isinstance(source_config, definition.config_type):
            raise TypeError(
                f"Expected config type {definition.config_type.__name__} for "
                f"provider '{self._provider_id.value}'"
            )
        return source_config

    def _get_provider_factory(self) -> ProviderServiceFactory:
        """Lazily create and cache the provider service factory."""
        if self._provider_factory is None:
            self._provider_factory = ProviderServiceFactory(
                self._config,
                self._get_provider_definition(),
                self._resolve_provider_config,
                logger=self._logger,
                metrics=self._metrics,
            )
        return self._provider_factory

    def create_extraction_service(self) -> Any:
        """Create extraction service for the configured provider."""
        return self._get_provider_factory().create_extraction_service()

    def create_normalization_service(self) -> NormalizationServiceABC:
        """Create normalization service for the configured provider."""
        return self._get_provider_factory().create_normalization_service()


__all__ = [
    "ApplicationServiceFactory",
    "ApplicationServiceFactoryABC",
]
