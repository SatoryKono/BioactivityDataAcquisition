"""
Factory for creating provider services (extraction, normalization).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Callable, cast

from bioetl.application.providers import ApplicationFieldProvider
from bioetl.domain.configs import PipelineConfig
from bioetl.domain.observability.contracts import LoggingPortABC, MetricsPortABC
from bioetl.domain.providers import ProviderDefinition
from bioetl.domain.transform.contracts import NormalizationServiceABC


class ProviderServiceFactoryABC(ABC):
    """Abstract factory for creating provider-specific services.

    Defines the contract for factories that create extraction and
    normalization services based on provider configuration.
    """

    @abstractmethod
    def create_normalization_service(self) -> NormalizationServiceABC:
        """Create normalization service for the configured provider.

        Returns:
            NormalizationServiceABC instance for data normalization.
        """

    @abstractmethod
    def create_extraction_service(self) -> Any:
        """Create the extraction service based on provider configuration.

        Returns:
            Extraction service instance for data retrieval.
        """


class ProviderServiceFactory(ProviderServiceFactoryABC):
    """Factory for creating provider-specific services."""

    def __init__(
        self,
        config: PipelineConfig,
        provider_definition: ProviderDefinition,
        resolve_provider_config: Callable[[ProviderDefinition], Any],
        *,
        logger: LoggingPortABC | None = None,
        metrics: MetricsPortABC | None = None,
    ) -> None:
        self._config = config
        self._provider_definition = provider_definition
        self._resolve_provider_config = resolve_provider_config
        self._logger = logger
        self._metrics = metrics

    def create_normalization_service(self) -> NormalizationServiceABC:
        """Create normalization service for the configured provider."""
        source_config = self._resolve_provider_config(self._provider_definition)
        components = self._provider_definition.components

        factory = cast(
            Callable[..., NormalizationServiceABC] | None,
            getattr(components, "create_normalization_service", None),
        )
        if factory is None:
            raise ValueError(
                f"Unsupported provider for normalization: {self._config.provider}"
            )
        return factory(source_config, pipeline_config=self._config)

    def create_extraction_service(self) -> Any:
        """Create the extraction service based on provider configuration."""
        source_config = self._resolve_provider_config(self._provider_definition)
        components = self._provider_definition.components

        # Inject application-level defaults
        field_provider = ApplicationFieldProvider()

        # Pass logger and metrics to create_extraction_service
        # It will create client internally if needed
        return components.create_extraction_service(
            source_config,
            field_provider=field_provider,
            logger=self._logger,
            metrics=self._metrics,
        )
