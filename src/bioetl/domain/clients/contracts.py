"""
Domain contracts for data clients.
"""

from abc import ABC, abstractmethod
from typing import Any, Iterator

Record = dict[str, Any]


class DataClientABC(ABC):
    """Universal data source client contract.

    Supports extraction of arbitrary entities through a unified ``fetch``
    method with filters, as well as side operations (pagination, metadata,
    resource release).
    """

    @abstractmethod
    def fetch(self, entity: str, **filters: Any) -> Any:
        """Execute query to data source for specified entity.

        Args:
            entity: Entity/endpoint name (provider-specific).
            **filters: Filters or query parameters.
        """

    @abstractmethod
    def iter_pages(self, request: Any) -> Iterator[Any]:
        """Iterator over result pages for a pre-built request.

        request: Request object (implementation-specific).
        """

    @abstractmethod
    def metadata(self) -> dict[str, Any]:
        """Source metadata (version, release)."""

    @abstractmethod
    def close(self) -> None:
        """Release resources (sessions, connections)."""
