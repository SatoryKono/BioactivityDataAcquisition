"""Port for infrastructure component factories.

This module defines abstract interfaces for creating infrastructure
components, allowing the application layer to request components
without depending on their concrete implementations.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from bioetl.domain.clients.base.contracts import RateLimiterABC


class InfrastructureFactoryPortABC(ABC):
    """Abstract factory for infrastructure components.

    This port abstracts the creation of infrastructure components,
    providing a clean interface for dependency injection.

    Example:
        >>> class DefaultInfraFactory(InfrastructureFactoryPortABC):
        ...     def create_rate_limiter(self, rate: float, **kwargs) -> RateLimiterABC:
        ...         return TokenBucketRateLimiter(rate=rate)
        ...     def create_http_session(self) -> Any:
        ...         return requests.Session()
    """

    @abstractmethod
    def create_rate_limiter(
        self,
        rate: float,
        *,
        capacity: float | None = None,
        **kwargs: Any,
    ) -> "RateLimiterABC":
        """Create rate limiter instance.

        Args:
            rate: Tokens per second.
            capacity: Maximum bucket capacity (defaults to rate).
            **kwargs: Additional implementation-specific arguments.

        Returns:
            Configured RateLimiterABC instance.
        """
        ...

    @abstractmethod
    def create_http_session(self) -> Any:
        """Create HTTP session instance.

        This method abstracts the creation of HTTP sessions, allowing
        the interfaces layer to obtain sessions without importing
        HTTP libraries directly.

        Returns:
            HTTP session instance (e.g., requests.Session).
        """
        ...


class ABCRegistryResolverPortABC(ABC):
    """Abstract port for resolving ABC implementations.

    This port provides a registry-based mechanism for resolving
    concrete implementations of abstract base classes.

    Example:
        >>> resolver: ABCRegistryResolverPortABC = ...
        >>> loader_class = resolver.resolve("LoaderABC")
        >>> loader = resolver.resolve_instance("LoaderABC", config=config)
    """

    @abstractmethod
    def resolve(self, abc_name: str) -> type:
        """Resolve implementation class for given ABC name.

        Args:
            abc_name: Name of the abstract base class.

        Returns:
            Concrete implementation class.

        Raises:
            KeyError: If no implementation is registered for the ABC.
        """
        ...

    @abstractmethod
    def resolve_instance(self, abc_name: str, **kwargs: Any) -> object:
        """Resolve and instantiate implementation for given ABC name.

        Args:
            abc_name: Name of the abstract base class.
            **kwargs: Arguments to pass to the constructor.

        Returns:
            Instantiated implementation object.

        Raises:
            KeyError: If no implementation is registered for the ABC.
        """
        ...

    @abstractmethod
    def resolve_default_factory(self, abc_name: str) -> Any:
        """Resolve default factory function for given ABC name.

        Args:
            abc_name: Name of the abstract base class.

        Returns:
            Factory function that creates instances of the implementation.

        Raises:
            KeyError: If no implementation is registered for the ABC.
        """
        ...


__all__ = ["ABCRegistryResolverPortABC", "InfrastructureFactoryPortABC"]
