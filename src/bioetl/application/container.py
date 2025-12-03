"""
Dependency Injection Container for the application.
"""
from typing import Any

from bioetl.domain.schemas import register_schemas
from bioetl.domain.schemas.registry import SchemaRegistry
from bioetl.domain.transform.hash_service import HashService
from bioetl.domain.validation.service import ValidationService
from bioetl.clients.records.factories import (
    default_normalization_service,
    default_record_source,
)
from bioetl.infrastructure.clients.chembl.factories import (
    default_chembl_extraction_service,
)
from bioetl.infrastructure.config.models import (
    ChemblSourceConfig,
    PipelineConfig,
)
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
        if self.config.provider == "chembl":
            source_config = self.config.get_source_config("chembl")
            if not isinstance(source_config, ChemblSourceConfig):
                raise TypeError("Expected ChemblSourceConfig")
            return default_chembl_extraction_service(source_config)

        raise ValueError(f"Unknown provider: {self.config.provider}")

    def get_hash_service(self) -> HashService:
        """Get the hash service."""
        return HashService()

    def get_record_source(self, extraction_service: Any, *, limit: int | None = None) -> Any:
        """Get record source based on configuration."""
        return default_record_source(
            config=self.config,
            extraction_service=extraction_service,
            limit=limit,
        )

    def get_normalization_service(self) -> Any:
        """Get record-level normalization service."""
        return default_normalization_service(self.config)


def build_pipeline_dependencies(config: PipelineConfig) -> PipelineContainer:
    """Factory for the container."""
    return PipelineContainer(config)
