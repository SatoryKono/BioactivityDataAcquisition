"""Application-level dependency container."""
from typing import Any

from bioetl.infrastructure.clients.chembl.factories import (
    default_chembl_extraction_service,
)
from bioetl.infrastructure.config.models import PipelineConfig
from bioetl.infrastructure.logging.contracts import LoggerAdapterABC
from bioetl.infrastructure.logging.factories import default_logger
from bioetl.infrastructure.output.contracts import OutputServiceABC
from bioetl.infrastructure.output.factories import default_output_service
from bioetl.infrastructure.validation.contracts import ValidationServiceABC
from bioetl.infrastructure.validation.factories import default_validation_service
from bioetl.domain.transform.hash_service import HashService


class PipelineContainer:
    """DI контейнер для пайплайнов."""

    def __init__(self, config: PipelineConfig) -> None:
        self.config = config
        self._validation_service: ValidationServiceABC | None = None

    def get_logger(self) -> LoggerAdapterABC:
        return default_logger()

    def get_validation_service(self) -> ValidationServiceABC:
        if self._validation_service is None:
            self._validation_service = default_validation_service()
        return self._validation_service

    def get_output_service(self) -> OutputServiceABC:
        return default_output_service(self.config.determinism)

    def get_extraction_service(self) -> Any:
        if self.config.provider == "chembl":
            return default_chembl_extraction_service()
        raise ValueError(f"Unknown provider: {self.config.provider}")

    def get_hash_service(self) -> HashService:
        return HashService()

    # Backward compatibility for legacy naming
    def get_output_writer(self) -> OutputServiceABC:
        return self.get_output_service()


def build_pipeline_dependencies(config: PipelineConfig) -> PipelineContainer:
    """Factory helper for pipeline dependencies."""
    return PipelineContainer(config)
