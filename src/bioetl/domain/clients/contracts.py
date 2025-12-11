"""Domain contracts for data clients.

This module defines the core abstractions for data source clients.
Clients provide unified access to external data sources (APIs, databases)
with support for pagination, metadata, and resource management.

Protocols:
    DataClientABC: Base contract for all data clients.
    DataClientWithBuilderABC: Extended contract for clients with request builder.
"""

from abc import ABC, abstractmethod
from typing import Any, Iterator, Protocol, runtime_checkable

from bioetl.domain.clients.base.contracts import RequestBuilderABC

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


@runtime_checkable
class DataClientWithBuilderProtocol(Protocol):
    """Protocol for data clients that expose a request builder.

    This protocol extends the basic data client contract with a typed
    request_builder property. Use this when you need access to the
    builder for advanced request construction.

    Example:
        >>> def extract(client: DataClientWithBuilderProtocol) -> None:
        ...     url = client.request_builder.build_for_endpoint("activity").build({})
        ...     for page in client.iter_pages(url):
        ...         process(page)
    """

    @property
    def request_builder(self) -> RequestBuilderABC:
        """Return the request builder for this client."""
        ...

    def fetch(self, entity: str, **filters: Any) -> Any:
        """Execute query to data source."""
        ...

    def iter_pages(self, request: Any) -> Iterator[Any]:
        """Iterator over result pages."""
        ...

    def metadata(self) -> dict[str, Any]:
        """Source metadata."""
        ...

    def close(self) -> None:
        """Release resources."""
        ...


class DataClientWithBuilderABC(DataClientABC):
    """Abstract base class for clients with request builder.

    This ABC extends DataClientABC with a required request_builder property.
    Use this when implementing clients that need builder-based request
    construction.

    Implementations must provide both the base DataClientABC methods
    and the request_builder property.
    """

    @property
    @abstractmethod
    def request_builder(self) -> RequestBuilderABC:
        """Return the request builder for this client.

        The builder is used to construct API requests with proper
        endpoint configuration and pagination.
        """
