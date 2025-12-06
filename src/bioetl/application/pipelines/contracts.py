"""
Contracts for pipeline components.
"""

from abc import ABC, abstractmethod
from typing import Any, Callable, Iterable

import pandas as pd

from bioetl.clients.base.logging.contracts import LoggerAdapterABC
from bioetl.domain.configs import PipelineConfig
from bioetl.domain.pipelines.contracts import ErrorPolicyABC, PipelineHookABC
from bioetl.domain.record_source import RecordSource
from bioetl.domain.transform.contracts import NormalizationServiceABC
from bioetl.domain.transform.hash_service import HashService
from bioetl.domain.transform.transformers import TransformerABC
from bioetl.domain.validation.service import ValidationService
from bioetl.infrastructure.output.unified_writer import UnifiedOutputWriter


class ExtractorABC(ABC):
    """
    Component responsible for extracting data from source.
    """

    @abstractmethod
    def extract(self, **kwargs: Any) -> Iterable[pd.DataFrame]:
        """
        Yields chunks of data.
        """


class LoaderABC(ABC):
    """
    Component responsible for loading data to destination.
    """

    @abstractmethod
    def load(self, df: pd.DataFrame, **kwargs: Any) -> None:
        """
        Loads data to destination.
        """


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
    def get_logger(self) -> LoggerAdapterABC:
        """Return configured logger adapter for pipeline run."""

    @abstractmethod
    def get_validation_service(self) -> ValidationService:
        """Return validation service bound to registered schemas."""

    @abstractmethod
    def get_output_writer(self) -> UnifiedOutputWriter:
        """Return unified writer for data, metadata and QC outputs."""

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
        logger: LoggerAdapterABC | None = None,
    ) -> RecordSource:
        """Return record source for pipeline input according to config."""

    @abstractmethod
    def get_hash_service(self) -> HashService:
        """Return hash service used for checksum generation."""

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


__all__ = [
    "ExtractorABC",
    "LoaderABC",
    "PipelineContainerABC",
]
