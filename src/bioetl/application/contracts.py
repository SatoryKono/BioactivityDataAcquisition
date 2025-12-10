"""Application-level contracts for pipeline infrastructure.

This module defines the core abstractions used by the dependency injection
container and pipeline factories. These contracts belong to the application
layer and should not depend on domain models beyond configuration and ports.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Callable

from bioetl.domain.clients.base.output.contracts import RunMetadataBuilderProtocol
from bioetl.domain.configs import PipelineConfig
from bioetl.domain.observability import LoggingPortABC
from bioetl.domain.pipelines.contracts import (
    ErrorPolicyABC,
    LoaderABC,
    PipelineHookABC,
)
from bioetl.domain.record_source import RecordSourceABC
from bioetl.domain.transform.contracts import (
    HashServiceABC,
    IndexGeneratorABC,
    NormalizationServiceABC,
    TimestampProviderABC,
)
from bioetl.domain.transform.transformers import TransformerABC
from bioetl.domain.validation.service import ValidationService

if TYPE_CHECKING:
    from bioetl.application.pipelines.base import PipelineBase


class PipelineContainerABC(ABC):
    """
    Dependency container contract for assembling pipelines.

    Provides factories for core pipeline services, including logging, validation,
    extraction, normalization, record sourcing, hashing, post-transformation,
    hooks, and error handling.
    """

    @property
    @abstractmethod
    def config(self) -> PipelineConfig:
        """Pipeline configuration associated with the container."""

    @abstractmethod
    def get_logger(self) -> LoggingPortABC:
        """Return configured logger adapter for pipeline run."""

    @abstractmethod
    def get_validation_service(self) -> ValidationService:
        """Return validation service bound to registered schemas."""

    @abstractmethod
    def get_loader(self) -> LoaderABC:
        """Return unified loader for data, metadata and QC outputs."""

    @abstractmethod
    def get_extraction_service(self) -> Any:
        """Return extraction service for the configured provider."""

    @abstractmethod
    def get_normalization_service(self) -> NormalizationServiceABC:
        """Return normalization service for the configured provider."""

    @abstractmethod
    def get_record_source(
        self,
        extraction_service: Any,
        *,
        limit: int | None = None,
        logger: LoggingPortABC | None = None,
        model_cls: type | None = None,
        batch_adapter: Any | None = None,
    ) -> RecordSourceABC:
        """Return record source for pipeline input according to config."""

    @abstractmethod
    def get_hash_service(self) -> HashServiceABC:
        """Return hash service used for checksum generation."""

    @abstractmethod
    def get_index_generator(self) -> IndexGeneratorABC:
        """Return index generator."""

    @abstractmethod
    def get_timestamp_provider(self) -> TimestampProviderABC:
        """Return timestamp provider."""

    @abstractmethod
    def get_post_transformer(
        self, *, version_provider: Callable[[], str] | None = None
    ) -> TransformerABC:
        """Return configured post-transformer chain."""

    @abstractmethod
    def get_hooks(self) -> list[PipelineHookABC]:
        """Return pipeline execution hooks."""

    @abstractmethod
    def get_error_policy(self) -> ErrorPolicyABC:
        """Return error handling policy for pipeline stages."""

    @abstractmethod
    def get_metadata_builder(self) -> RunMetadataBuilderProtocol:
        """Return builder for run metadata artifacts."""


class PipelineFactoryABC(ABC):
    """
    Abstract factory for creating pipeline instances.

    Each pipeline type (e.g., ChEMBL, PubChem) provides a concrete implementation
    that knows how to assemble the pipeline with its specific dependencies.
    """

    @abstractmethod
    def create(
        self,
        container: PipelineContainerABC,
        *,
        limit: int | None = None,
    ) -> PipelineBase:
        """
        Create a fully configured pipeline instance.

        Args:
            container: Dependency injection container providing services.
            limit: Optional record limit for extraction.

        Returns:
            Configured pipeline ready to run.
        """


__all__ = [
    "PipelineContainerABC",
    "PipelineFactoryABC",
]
