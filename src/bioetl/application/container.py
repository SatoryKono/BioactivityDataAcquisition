"""
Dependency Injection Container for the application.
"""
from typing import Any

from bioetl.domain.schemas import register_schemas
from bioetl.domain.schemas.registry import SchemaRegistry
from bioetl.domain.transform.hash_service import HashService
from bioetl.domain.validation.service import ValidationService
from bioetl.infrastructure.clients.chembl.factories import (
    default_chembl_extraction_service,
)
from bioetl.infrastructure.config.models import PipelineConfig
from bioetl.infrastructure.config.source_chembl import ChemblSourceConfig
from bioetl.infrastructure.logging.contracts import LoggerAdapterABC
from bioetl.infrastructure.logging.factories import default_logger
from bioetl.infrastructure.output.factories import (
    default_metadata_writer,
    default_writer,
)
from bioetl.infrastructure.output.services.metadata_builder import (
    MetadataBuilder,
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

    def get_metadata_builder(self) -> MetadataBuilder:
        """Get the metadata builder service."""
        return MetadataBuilder()

    def get_output_writer(self) -> UnifiedOutputWriter:
        """Get the unified output writer."""
        return UnifiedOutputWriter(
            writer=default_writer(),
            metadata_writer=default_metadata_writer(),
            config=self.config.determinism,
            metadata_builder=self.get_metadata_builder()
        )

    def get_extraction_service(self) -> Any:
        """Get the extraction service based on provider configuration."""
        if self.config.provider == "chembl":
            # Extract chembl config from generic sources dict
            raw_source_config = self.config.sources.get("chembl", {})
            # Validate/Parse it into ChemblSourceConfig
            source_config = ChemblSourceConfig(**raw_source_config)
            return default_chembl_extraction_service(
                source_config=source_config
            )
        else:
            raise ValueError(f"Unknown provider: {self.config.provider}")

    def get_hash_service(self) -> HashService:
        """Get the hash service."""
        return HashService()


def build_pipeline_dependencies(config: PipelineConfig) -> PipelineContainer:
    """Factory for the container."""
    return PipelineContainer(config)
