"""Ports for extraction services (domain layer)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable
from typing import Any, Protocol

from bioetl.domain.data import RecordBatch
from bioetl.domain.types import ApiPayload

# Type aliases for backward compatibility
RawRecordDict = dict[str, Any]
"""Type alias for a single raw record dictionary.

Deprecated: Use dict[str, Any] directly or Record from domain.data.
This alias is maintained for backward compatibility with existing tests.
"""

RawRecordBatch = RecordBatch
"""Type alias for a batch of raw records.

Deprecated: Use RecordBatch from domain.data instead.
This alias is maintained for backward compatibility with existing tests.
"""


class RecordFetcherABC(ABC):
    """Contract for raw record providers with pagination support.

    This abstract base class defines the interface for fetching raw records
    from external data sources. Implementations should return generic dicts
    rather than domain models to maintain layer separation.
    """

    @abstractmethod
    def iter_extract(
        self, entity: str, *, chunk_size: int | None = None, **filters: object
    ) -> Iterable[RecordBatch]:
        """Iterate over batches of raw records.

        Args:
            entity: The entity type to extract (e.g., 'molecule', 'activity').
            chunk_size: Optional batch size for pagination.
            **filters: Additional filters to apply during extraction.

        Returns:
            Iterable of record batches as list[dict[str, Any]].
            Domain model mapping should happen in application layer.

        Yields:
            Batches of raw records as dictionaries.
        """

    @abstractmethod
    def extract_all(self, entity: str, **filters: object) -> RecordBatch:
        """Return all records for entity as raw dicts.

        Args:
            entity: The entity type to extract.
            **filters: Additional filters to apply.

        Returns:
            All matching records as list[dict[str, Any]].
        """


class VersionProviderABC(ABC):
    """Provider of data source version information."""

    @abstractmethod
    def get_release_version(self) -> str:
        """Get raw data source version identifier (e.g., '34').

        Returns:
            Raw version string without provider prefix.
            Use domain.services.version_formatter for formatted output.
        """


class ExtractionServiceABC(RecordFetcherABC):
    """Extended extraction service with versioning and serialization.

    Inherits base methods iter_extract() and extract_all() from RecordFetcherABC.
    Adds methods for working with versions, batches, and serialization.
    """

    @abstractmethod
    def get_release_version(self) -> str:
        """Get raw data source version identifier (e.g., '34')."""

    @abstractmethod
    def request_batch(
        self, entity: str, batch_ids: list[str], filter_key: str
    ) -> dict[str, object]:
        """Request batch by IDs, return raw API response.

        Args:
            entity: Entity name.
            batch_ids: List of IDs to request.
            filter_key: Filter parameter key for ID lookup.

        Returns:
            Raw API response as dictionary.
        """

    @abstractmethod
    def parse_response(self, raw_response: object) -> RecordBatch:
        """Parse raw response into record dicts.

        Args:
            raw_response: Raw API response object.

        Returns:
            Parsed records as list[dict[str, Any]].
        """

    @abstractmethod
    def serialize_records(self, entity: str, records: list[object]) -> RecordBatch:
        """Serialize records for storage or further processing.

        Args:
            entity: Entity name.
            records: List of records to serialize.

        Returns:
            Serialized records as list[dict[str, Any]].
        """


class BatchAdapterABC(Protocol):
    """Protocol for adapting raw batches to list of record dicts.

    Used to normalize different batch formats from extraction services
    into the expected RecordBatch format.
    """

    def process_batch(self, raw_batch: object) -> RecordBatch:
        """Normalize a batch into a list of raw record mappings.

        Args:
            raw_batch: Raw batch from extraction service (DataFrame, dict, list, etc.)

        Returns:
            List of record dictionaries.
        """
        ...


__all__ = [
    # Canonical type aliases
    "RecordBatch",  # from domain.data
    "ApiPayload",  # from domain.types
    # Deprecated type aliases (for backward compatibility)
    "RawRecordDict",
    "RawRecordBatch",
    # Abstract base classes
    "RecordFetcherABC",
    "VersionProviderABC",
    "ExtractionServiceABC",
    # Protocols
    "BatchAdapterABC",
]
