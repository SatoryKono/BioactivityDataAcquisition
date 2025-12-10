"""Ports for parsing external API responses.

This module defines abstract contracts for parsing raw API responses
without domain model knowledge, following hexagonal architecture principles.
Infrastructure adapters implement these ports to parse provider-specific responses
into generic record dictionaries.

Migration Guide (from ResponseParserABC):
-----------------------------------------
``ResponseParserABC`` from ``bioetl.domain.clients.base.contracts`` is deprecated.
Use ``ResponseParserPortABC`` from this module instead.

Method mapping:
    - ``parse(raw_response)`` → ``parse_to_records(raw_response)``
    - ``parse_response(raw_response)`` → ``parse_to_records(raw_response)`` (was deprecated)
    - ``extract_metadata(raw_response)`` → ``extract_pagination(raw_response)``

Type changes:
    - Generic[RecordT] (Pydantic models) → RawRecordList (untyped dicts)
    - This change improves layer isolation (infrastructure doesn't import domain models)

Example migration::

    # Before (deprecated)
    from bioetl.domain.clients.base.contracts import ResponseParserABC

    class MyParser(ResponseParserABC[MyModel]):
        def parse(self, raw_response): ...
        def extract_metadata(self, raw_response): ...

    # After (recommended)
    from bioetl.domain.ports.parsing import ResponseParserPortABC

    class MyParser(ResponseParserPortABC):
        def parse_to_records(self, raw_response): ...
        def extract_pagination(self, raw_response): ...
"""

from __future__ import annotations

import warnings
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, TypeAlias

from bioetl.domain.record_source import SourceRecord

# Generic type aliases for infrastructure layer
# These allow infrastructure code to work without importing domain models
RawPayload: TypeAlias = dict[str, Any]
RawRecordDict: TypeAlias = dict[str, Any]
RawRecordList: TypeAlias = list[RawRecordDict] | list[SourceRecord]


class ResponseParserPortABC(ABC):
    """Port for parsing raw API responses without domain model knowledge.

    This abstract base class defines the contract for parsing raw API responses
    into generic record dictionaries. Implementations in infrastructure layer
    can parse provider-specific response formats while domain layer remains
    decoupled from those details.

    Example:
        >>> class ChemblParserAdapter(ResponseParserPortABC):
        ...     def parse_to_records(self, raw_response):
        ...         # Extract records from ChEMBL-specific response structure
        ...         for key, value in raw_response.items():
        ...             if isinstance(value, list):
        ...                 return value
        ...         return []
        ...
        ...     def extract_pagination(self, raw_response):
        ...         return raw_response.get("page_meta", {})
    """

    @abstractmethod
    def parse_to_records(self, raw_response: RawPayload) -> RawRecordList:
        """Parse raw API response into list of untyped record dicts.

        Args:
            raw_response: Raw dictionary payload from API response.

        Returns:
            List of record dictionaries without type validation.
            Returns empty list if no records found.
        """

    @abstractmethod
    def extract_pagination(
        self, raw_response: RawPayload
    ) -> dict[str, int | str | None]:
        """Extract pagination metadata from response.

        Args:
            raw_response: Raw dictionary payload from API response.

        Returns:
            Dictionary containing pagination metadata such as
            total_count, offset, limit, next_url, etc.
            Keys depend on provider implementation.
        """

    # =========================================================================
    # Backward compatibility aliases (from deprecated ResponseParserABC)
    # =========================================================================

    def parse(self, raw_response: RawPayload) -> RawRecordList:
        """Backward-compatible alias for :meth:`parse_to_records`.

        .. deprecated:: 2.0
            Use :meth:`parse_to_records` instead. Will be removed in 3.0.

        Args:
            raw_response: Raw dictionary payload from API response.

        Returns:
            List of record dictionaries without type validation.
        """
        warnings.warn(
            "parse() is deprecated, use parse_to_records() instead. "
            "See migration guide in bioetl.domain.ports.parsing docstring.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.parse_to_records(raw_response)

    def extract_metadata(
        self, raw_response: RawPayload
    ) -> dict[str, int | str | None]:
        """Backward-compatible alias for :meth:`extract_pagination`.

        .. deprecated:: 2.0
            Use :meth:`extract_pagination` instead. Will be removed in 3.0.

        Args:
            raw_response: Raw dictionary payload from API response.

        Returns:
            Dictionary containing pagination/metadata information.
        """
        warnings.warn(
            "extract_metadata() is deprecated, use extract_pagination() instead. "
            "See migration guide in bioetl.domain.ports.parsing docstring.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.extract_pagination(raw_response)


@dataclass(frozen=True, slots=True)
class PaginationInfo:
    """Value object for pagination metadata.

    Immutable container for pagination state extracted from API responses.
    Used to track position in paginated result sets.

    Attributes:
        total_count: Total number of records available (None if unknown).
        offset: Current offset/starting position in result set.
        limit: Maximum records per page/request.
        next_url: URL for next page if cursor-based pagination (None if N/A).
    """

    total_count: int | None = None
    offset: int = 0
    limit: int = 0
    next_url: str | None = None

    @property
    def has_more(self) -> bool:
        """Check if more pages are available.

        Returns:
            True if there are more records to fetch, False otherwise.
            Returns True if next_url is set or if offset + limit < total_count.
        """
        if self.next_url is not None:
            return True
        if self.total_count is not None:
            return self.offset + self.limit < self.total_count
        return False

    @classmethod
    def from_dict(cls, data: dict[str, int | str | None]) -> PaginationInfo:
        """Create PaginationInfo from a metadata dictionary.

        Args:
            data: Dictionary with pagination fields
                (total_count, offset, limit, next_url).

        Returns:
            New PaginationInfo instance with extracted values.
        """
        total = data.get("total_count")
        offset = data.get("offset")
        limit = data.get("limit")
        next_url = data.get("next_url")
        return cls(
            total_count=total if isinstance(total, int) else None,
            offset=offset if isinstance(offset, int) else 0,
            limit=limit if isinstance(limit, int) else 0,
            next_url=next_url if isinstance(next_url, str) else None,
        )


__all__ = [
    "RawPayload",
    "RawRecordDict",
    "RawRecordList",
    "ResponseParserPortABC",
    "PaginationInfo",
]
