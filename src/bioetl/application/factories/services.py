"""
Factory for creating provider services (extraction, normalization).
"""

from __future__ import annotations

from typing import Any, Callable, cast

from bioetl.application.providers import ApplicationFieldProvider
from bioetl.domain.configs import PipelineConfig
from bioetl.domain.providers import ProviderDefinition
from bioetl.domain.transform.contracts import NormalizationServiceABC


class ProviderServiceFactory:
    """Factory for creating provider-specific services."""

    def __init__(
        self,
        config: PipelineConfig,
        provider_definition: ProviderDefinition,
        resolve_provider_config: Callable[[ProviderDefinition], Any],
    ) -> None:
        self._config = config
        self._provider_definition = provider_definition
        self._resolve_provider_config = resolve_provider_config

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

        client = components.create_client(source_config)

        # Inject application-level defaults
        field_provider = ApplicationFieldProvider()

        return components.create_extraction_service(
            source_config, client=client, field_provider=field_provider
        )
