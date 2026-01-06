"""Port for ID Mapping services.

Defines IDMappingPort for mapping identifiers between databases.
Used for ChEMBL → UniProt and similar cross-database mappings.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol, Self, runtime_checkable

from bioetl.domain.types import HealthStatus


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
        exc_tb: Any,
    ) -> None:
        """Exit async context manager."""
        ...

    async def map_ids(
        self,
        from_db: str,
        to_db: str,
        ids: list[str],
    ) -> Mapping[str, str | None]:
        """Map identifiers from source database to target database.

        Args:
            from_db: Source database name (e.g., 'ChEMBL').
            to_db: Target database name (e.g., 'UniProtKB').
            ids: List of identifiers to map.

        Returns:
            Dictionary mapping each input ID to its mapped value,
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
