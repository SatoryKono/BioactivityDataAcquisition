"""Ports for extraction services (domain layer)."""

from __future__ import annotations

import warnings
from abc import ABC, abstractmethod
from collections.abc import Iterable
from typing import TYPE_CHECKING, Protocol

from bioetl.domain.types import (
    ApiPayload,
    RawRecord,
    RecordBatch,
)

# =============================================================================
# Deprecated Type Aliases (backward compatibility re-exports)
# =============================================================================
# Import from bioetl.domain.types for new code.
# These re-exports emit deprecation warnings via __getattr__ below.

__all__: list[str] = []  # Populated at end of module

# Sentinel for lazy deprecation
_DEPRECATED_TYPE_ALIASES = {
    "RawRecordDict": "RawRecord",
    "RawRecordBatch": "RecordBatch",
}

if TYPE_CHECKING:
    from bioetl.domain.record_source import SourceRecord


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
    def serialize_records(self, entity: str, records: list[object]) -> RawRecordBatch:
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


# =============================================================================
# Backward Compatibility Helpers
# =============================================================================


def to_raw_records(batch: RecordBatch) -> list["SourceRecord"]:
    """Convert raw dicts to SourceRecord models (migration helper).

    DEPRECATED: Use application layer mappers instead.
    This function is provided for gradual migration from SourceRecord models
    to generic dicts in extraction services.

    Args:
        batch: List of raw record dictionaries.

    Returns:
        List of SourceRecord Pydantic models.

    Example:
        >>> from bioetl.domain.ports.extraction import to_raw_records
        >>> dicts = [{"id": "1", "name": "test"}]
        >>> records = to_raw_records(dicts)  # DeprecationWarning
    """
    warnings.warn(
        "to_raw_records is deprecated. Use RecordMapperABC in application layer.",
        DeprecationWarning,
        stacklevel=2,
    )
    from bioetl.domain.record_source import SourceRecord

    return [SourceRecord.model_validate(record) for record in batch]


def from_raw_records(records: list["SourceRecord"]) -> RecordBatch:
    """Convert SourceRecord models to raw dicts (migration helper).

    DEPRECATED: Use application layer mappers instead.
    This function is provided for gradual migration from SourceRecord models
    to generic dicts in extraction services.

    Args:
        records: List of SourceRecord Pydantic models.

    Returns:
        List of raw record dictionaries.
    """
    warnings.warn(
        "from_raw_records is deprecated. Return dicts directly from extraction.",
        DeprecationWarning,
        stacklevel=2,
    )
    return [record.model_dump() for record in records]


# =============================================================================
# Module __getattr__ for deprecated type alias access
# =============================================================================


def __getattr__(name: str) -> type:
    """Emit deprecation warning for legacy type alias imports.

    Enables backward-compatible imports like:
        from bioetl.domain.ports.extraction import RawRecordDict

    But emits a DeprecationWarning directing users to the new location.
    """
    if name in _DEPRECATED_TYPE_ALIASES:
        new_name = _DEPRECATED_TYPE_ALIASES[name]
        warnings.warn(
            f"{name} is deprecated, use {new_name} from bioetl.domain.types instead. "
            "See migration guide in bioetl.domain.types module docstring.",
            DeprecationWarning,
            stacklevel=2,
        )
        from bioetl.domain import types

        return getattr(types, new_name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    # Canonical type aliases (re-exported from domain.types)
    "RawRecord",
    "RecordBatch",
    "ApiPayload",
    # Deprecated type aliases (for backward compatibility)
    "RawRecordDict",
    "RawRecordBatch",
    # Abstract base classes
    "RecordFetcherABC",
    "VersionProviderABC",
    "ExtractionServiceABC",
    # Protocols
    "BatchAdapterABC",
    # Backward compatibility helpers
    "to_raw_records",
    "from_raw_records",
]
