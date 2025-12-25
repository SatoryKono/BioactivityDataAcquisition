"""Base Registry Protocol for unified registration pattern.

All registries (PipelineRegistry, DataSourceRegistry, etc.) should
follow this protocol for consistent API across the codebase.
"""

from __future__ import annotations

from typing import ClassVar, Protocol, TypeVar, runtime_checkable

K = TypeVar("K")  # Key type
V = TypeVar("V")  # Value type


@runtime_checkable
class RegistryProtocol(Protocol[K, V]):
    """Protocol defining the standard Registry interface.

    All registries MUST implement these methods for consistency.

    Example:
        >>> class MyRegistry(RegistryProtocol[str, Callable]):
        ...     _registry: ClassVar[dict[str, Callable]] = {}
        ...
        ...     @classmethod
        ...     def register(cls, key: str, value: Callable) -> None:
        ...         cls._registry[key] = value
    """

    _registry: ClassVar[dict[K, V]]

    @classmethod
    def register(cls, key: K, value: V) -> None:
        """Register a value with the given key.

        Args:
            key: Unique identifier for the registered item.
            value: The item to register.

        Raises:
            ValueError: If key is already registered (optional - warn instead).
        """
        ...

    @classmethod
    def get(cls, key: K) -> V:
        """Get a registered value by key.

        Args:
            key: The key to look up.

        Returns:
            The registered value.

        Raises:
            KeyError: If key is not registered.
        """
        ...

    @classmethod
    def list_keys(cls) -> list[K]:
        """List all registered keys.

        Returns:
            List of registered keys in registration order.
        """
        ...

    @classmethod
    def contains(cls, key: K) -> bool:
        """Check if a key is registered.

        Args:
            key: The key to check.

        Returns:
            True if key is registered, False otherwise.
        """
        ...

    @classmethod
    def clear(cls) -> None:
        """Clear all registrations (for testing).

        WARNING: Only use in tests. Not for production.
        """
        ...
