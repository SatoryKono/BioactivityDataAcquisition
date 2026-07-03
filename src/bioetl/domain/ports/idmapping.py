"""Port for ID Mapping services.

Defines IDMappingPort for mapping identifiers between databases.
Used for ChEMBL → UniProt and similar cross-database mappings.
"""

from __future__ import annotations

from collections.abc import Mapping
from types import TracebackType
from typing import Protocol, Self, runtime_checkable

from bioetl.domain.types import HealthStatus, JsonDict

__all__ = [
    "IDMappingPort",
    "IDMappingSourceReaderPort",
]


@runtime_checkable
class IDMappingPort(Protocol):
    """Port for ID mapping between databases.

    This interface abstracts ID mapping services that convert identifiers
    from one database format to another (e.g., ChEMBL → UniProt).

    Implementations may use REST APIs (UniProt ID Mapping), local databases,
    or other mapping services.
    """

    @property
    def provider_name(self) -> str:
        """The unique name of the mapping provider (e.g., 'uniprot_idmapping')."""
        ...

    async def __aenter__(self) -> Self:
        """Enter async context manager."""
        ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Exit async context manager."""
        ...

    async def map_ids(
        self,
        from_db: str,
        to_db: str,
        ids: list[str],
    ) -> Mapping[
        str,
        JsonDict | None,
    ]:
        """Map identifiers from source database to target database.

        Args:
            from_db: Source database name (e.g., 'ChEMBL').
            to_db: Target database name (e.g., 'UniProtKB').
            ids: List of identifiers to map.

        Returns:
            Dictionary mapping each input ID to its entry data dict,
            or None if no mapping was found.

        Raises:
            IDMappingJobError: If the mapping job fails.
            IDMappingTimeoutError: If the job times out.
        """
        ...

    async def health_check(self) -> HealthStatus:
        """Check the health of the mapping service.

        Returns:
            HealthStatus indicating the current status of the service.
        """
        ...


@runtime_checkable
class IDMappingSourceReaderPort(Protocol):
    """Port for reading ID mapping source identifiers from external storage.

    This interface abstracts file/database access used to load source IDs
    for mapping pipelines (e.g., ChEMBL IDs from CSV input).
    """

    async def read_ids(self, source_path: str, id_column: str) -> list[str]:
        """Read source identifiers from the given source path.

        Args:
            source_path: Source location reference or URI.
            id_column: Column name containing source IDs.

        Returns:
            Ordered list of non-empty source IDs.

        Raises:
            FileNotFoundError: If source does not exist.
            ValueError: If the column is missing.
        """
        ...

    async def source_exists(self, source_path: str) -> bool:
        """Check whether the source path exists.

        Args:
            source_path: Source location reference or URI.

        Returns:
            True if source exists, otherwise False.
        """
        ...
