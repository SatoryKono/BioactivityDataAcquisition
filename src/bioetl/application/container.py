"""Dependency Injection Container for the application."""
from typing import Any

import bioetl.infrastructure.clients.chembl.provider  # noqa: F401 - ensure registration
from bioetl.core.provider_registry import get_provider
from bioetl.core.providers import ProviderId
from bioetl.domain.schemas import register_schemas
from bioetl.domain.schemas.registry import SchemaRegistry
from bioetl.domain.transform.hash_service import HashService
from bioetl.domain.validation.service import ValidationService
from bioetl.infrastructure.config.models import PipelineConfig
from bioetl.infrastructure.logging.contracts import LoggerAdapterABC
from bioetl.infrastructure.logging.factories import default_logger
from bioetl.infrastructure.output.factories import (
    default_metadata_writer,
    default_writer,
)
from bioetl.infrastructure.output.unified_writer import UnifiedOutputWriter


class PipelineContainer:
    """
    DI Container for pipeline dependencies.
    """

    def __init__(self, config: PipelineConfig) -> None:
        self.config = config
        self._schema_registry = SchemaRegistry()
        register_schemas(self._schema_registry)

    def get_logger(self) -> LoggerAdapterABC:
        """Get the configured logger."""
        return default_logger()

    def get_validation_service(self) -> ValidationService:
        """Get the validation service with registered schemas."""
        return ValidationService(schema_provider=self._schema_registry)

    def get_output_writer(self) -> UnifiedOutputWriter:
        """Get the unified output writer."""
        return UnifiedOutputWriter(
            writer=default_writer(),
            metadata_writer=default_metadata_writer(),
            config=self.config.determinism,
        )

    def get_extraction_service(self) -> Any:
        """Get the extraction service based on provider configuration."""
        provider_id = ProviderId(self.config.provider)
        definition = get_provider(provider_id)
        source_config = self.config.get_source_config(provider_id)
        if not isinstance(source_config, definition.config_type):
            raise TypeError(
                f"Expected config type {definition.config_type.__name__} for "
                f"provider '{provider_id.value}'"
            )

        client = definition.components.create_client(source_config)
        return definition.components.create_extraction_service(client, source_config)

    def get_hash_service(self) -> HashService:
        """Get the hash service."""
        return HashService()


def build_pipeline_dependencies(config: PipelineConfig) -> PipelineContainer:
    """Factory for the container."""
    return PipelineContainer(config)
