from typing import Any

from bioetl.infrastructure.clients.chembl.factories import default_chembl_extraction_service
from bioetl.infrastructure.config.models import PipelineConfig
from bioetl.infrastructure.logging.contracts import LoggerAdapterABC
from bioetl.infrastructure.logging.factories import default_logger
from bioetl.infrastructure.output.factories import default_metadata_writer, default_writer
from bioetl.infrastructure.output.unified_writer import UnifiedOutputWriter
from bioetl.application.pipelines.chembl.extraction import ChemblExtractionService
from bioetl.domain.schemas import register_schemas
from bioetl.domain.schemas.registry import SchemaRegistry
from bioetl.domain.transform.hash_service import HashService
from bioetl.domain.validation.service import ValidationService


class PipelineContainer:
    """
    DI Container for pipeline dependencies.
    """

    def __init__(self, config: PipelineConfig) -> None:
        self.config = config
        self._schema_registry = SchemaRegistry()
        register_schemas(self._schema_registry)

    def get_logger(self) -> LoggerAdapterABC:
        return default_logger()

    def get_validation_service(self) -> ValidationService:
        return ValidationService(schema_provider=self._schema_registry)

    def get_output_writer(self) -> UnifiedOutputWriter:
        return UnifiedOutputWriter(
            writer=default_writer(),
            metadata_writer=default_metadata_writer(),
            config=self.config.determinism
        )

    def get_extraction_service(self) -> Any:
        if self.config.provider == "chembl":
            return default_chembl_extraction_service()
        else:
            raise ValueError(f"Unknown provider: {self.config.provider}")

    def get_hash_service(self) -> HashService:
        return HashService()


def build_pipeline_dependencies(config: PipelineConfig) -> PipelineContainer:
    """Factory for the container."""
    return PipelineContainer(config)
