"""
Transform component factory.

Provides factory for creating transform-related components
(hash service, index generator, timestamp provider, post transformer).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Callable

from bioetl.domain.configs import PipelineConfig
from bioetl.domain.transform.contracts import (
    HashServiceABC,
    IndexGeneratorABC,
    TimestampProviderABC,
)
from bioetl.domain.transform.factories import default_post_transformer
from bioetl.domain.transform.transformers import TransformerABC


class TransformComponentFactoryABC(ABC):
    """Abstract base for transform component factories."""

    @abstractmethod
    def get_hash_service(self) -> HashServiceABC:
        """Get the hash service."""

    @abstractmethod
    def get_index_generator(self) -> IndexGeneratorABC:
        """Get the index generator."""

    @abstractmethod
    def get_timestamp_provider(self) -> TimestampProviderABC:
        """Get the timestamp provider."""

    @abstractmethod
    def get_post_transformer(
        self, *, version_provider: Callable[[], str | None] | None = None
    ) -> TransformerABC:
        """Get the post transformer chain."""


class TransformComponentFactory(TransformComponentFactoryABC):
    """
    Factory for creating transform-related components.

    Encapsulates lazy creation of hash service, index generator,
    timestamp provider, and post transformer chain.

    All components (hash_service, index_generator, timestamp_provider)
    must be injected from outer layers (e.g. interfaces wiring or tests)
    to maintain clean architecture boundaries.
    """

    def __init__(
        self,
        config: PipelineConfig,
        hash_service: HashServiceABC | None = None,
        index_generator: IndexGeneratorABC | None = None,
        timestamp_provider: TimestampProviderABC | None = None,
    ) -> None:
        """
        Initialize the transform component factory.

        Args:
            config: Pipeline configuration.
            hash_service: Optional pre-configured hash service.
            index_generator: Optional pre-configured index generator.
            timestamp_provider: Optional pre-configured timestamp provider.
        """
        self._config = config
        self._hash_service = hash_service
        self._index_generator = index_generator
        self._timestamp_provider = timestamp_provider
        self._post_transformer: TransformerABC | None = None

    def get_hash_service(self) -> HashServiceABC:
        """Get the hash service.

        The concrete implementation must be injected from outer layers
        (e.g. interfaces wiring or tests) to avoid application →
        infrastructure dependencies.

        Raises:
            RuntimeError: If hash service is not configured.
        """
        if self._hash_service is None:
            raise RuntimeError("Hash service is not configured for this factory")
        return self._hash_service

    def get_index_generator(self) -> IndexGeneratorABC:
        """Get the index generator.

        The concrete implementation must be injected from outer layers
        (e.g. interfaces wiring or tests) to avoid application →
        infrastructure dependencies.

        Raises:
            RuntimeError: If index generator is not configured.
        """
        if self._index_generator is None:
            raise RuntimeError("Index generator is not configured for this factory")
        return self._index_generator

    def get_timestamp_provider(self) -> TimestampProviderABC:
        """Get the timestamp provider.

        The concrete implementation must be injected from outer layers
        (e.g. interfaces wiring or tests) to avoid application →
        infrastructure dependencies.

        Raises:
            RuntimeError: If timestamp provider is not configured.
        """
        if self._timestamp_provider is None:
            raise RuntimeError("Timestamp provider is not configured for this factory")
        return self._timestamp_provider

    def get_post_transformer(
        self, *, version_provider: Callable[[], str | None] | None = None
    ) -> TransformerABC:
        """Build the standard post-transformer chain.

        Creates a chain of transformers that add:
        - hash_business_key and hash_row columns
        - index column
        - database_version column
        - acquisition_timestamp column

        Args:
            version_provider: Optional callable returning database version.

        Returns:
            Configured transformer chain.
        """
        if self._post_transformer is None:
            self._post_transformer = default_post_transformer(
                hash_service=self.get_hash_service(),
                index_generator=self.get_index_generator(),
                timestamp_provider=self.get_timestamp_provider(),
                business_key_fields=self._config.quality.hashing.business_key_fields,
                version_provider=version_provider,
            )
        return self._post_transformer


__all__ = [
    "TransformComponentFactory",
    "TransformComponentFactoryABC",
]
