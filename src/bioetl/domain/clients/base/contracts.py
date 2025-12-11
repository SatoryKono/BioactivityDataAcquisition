"""Base contracts for data source helpers."""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")
RecordT = TypeVar("RecordT", bound=BaseModel)

if TYPE_CHECKING:
    pass


class RequestBuilderABC(ABC):
    """Builder pattern for request creation.

    This ABC provides a fluent interface for constructing API requests.
    Implementations should support endpoint configuration and pagination.

    Note:
        Consider using
        :class:`bioetl.domain.ports.request_building.RequestBuilderPortABC`
        for new code - it provides a cleaner port-based contract.
    """

    @abstractmethod
    def build_for_endpoint(self, endpoint: str) -> "RequestBuilderABC":
        """Configure builder for a specific API endpoint.

        Args:
            endpoint: The API endpoint name (e.g., 'activity', 'assay').

        Returns:
            Self for method chaining.
        """

    @abstractmethod
    def build_request(self, params: dict[str, Any]) -> Any:
        """Create request object from parameters."""

    @abstractmethod
    def build(self, endpoint: str, params: dict[str, Any] | None = None) -> Any:
        """Create request for specified endpoint with parameters."""

    @abstractmethod
    def build_with_pagination(self, offset: int, limit: int) -> "RequestBuilderABC":
        """Add pagination parameters."""


class PaginatorABC(ABC):
    """Pagination strategy."""

    @abstractmethod
    def get_items(self, response: Any) -> list[BaseModel]:
        """Extract items from response."""

    @abstractmethod
    def get_next_marker(self, response: Any) -> str | int | None:
        """Return next page marker (offset, cursor, url)."""

    @abstractmethod
    def has_more(self, response: Any) -> bool:
        """Check if there are more pages."""


class RateLimiterABC(ABC):
    """Request rate limiting."""

    @abstractmethod
    def acquire(self) -> None:
        """Request permission to execute (blocks if necessary)."""


class RetryPolicyABC(ABC):
    """Retry policy."""

    @property
    @abstractmethod
    def max_attempts(self) -> int:
        """Maximum number of attempts."""

    @abstractmethod
    def should_retry(self, error: Exception, attempt: int) -> bool:
        """Determine whether to retry."""

    @abstractmethod
    def get_backoff(self, attempt: int) -> float:
        """Return delay before next attempt (in seconds)."""


class CacheABC(ABC, Generic[T]):
    """Caching interface."""

    @abstractmethod
    def get(self, key: str) -> T | None:
        """Return value from cache or ``None``."""

    @abstractmethod
    def set(self, key: str, value: T, ttl: int | None = None) -> None:
        """Store value in cache with optional TTL in seconds."""

    @abstractmethod
    def invalidate(self, key: str) -> None:
        """Remove value from cache."""

    @abstractmethod
    def clear(self) -> None:
        """Clear entire cache."""


class SecretProviderABC(ABC):
    """Secret provider (env, vault)."""

    @abstractmethod
    def get_secret(self, name: str) -> str | None:
        """Return secret value."""
