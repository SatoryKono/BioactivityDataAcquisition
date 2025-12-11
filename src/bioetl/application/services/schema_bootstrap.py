"""Schema bootstrap service for initializing schema providers."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from bioetl.domain.schemas.registry import SchemaRegistry
from bioetl.domain.validation import SchemaProviderABC

if TYPE_CHECKING:
    pass


@dataclass
class SchemaBootstrapService:
    """Service for bootstrapping schema providers.

    This service ensures that schema providers are properly initialized
    with all required schemas before being used by pipeline components.
    It implements a lazy initialization pattern with caching.

    Example:
        >>> service = SchemaBootstrapService(register_fn=my_register_fn)
        >>> provider = service.ensure_registered()
        >>> # Provider now has all schemas registered
        >>> provider.get_schema("activity")
    """

    _schema_provider: SchemaProviderABC | None = field(default=None, repr=False)
    _registered: bool = field(default=False, repr=False)
    _register_fn: Callable[[SchemaProviderABC], Any] | None = field(
        default=None, repr=False
    )

    def ensure_registered(self) -> SchemaProviderABC:
        """Ensure schemas are registered and return the provider.

        Creates a schema provider if not already initialized, registers
        all default schemas, and returns the configured provider.

        Returns:
            Fully initialized schema provider with all schemas registered.

        Note:
            This method is idempotent - calling it multiple times returns
            the same provider instance.
        """
        if self._registered and self._schema_provider is not None:
            return self._schema_provider

        if self._schema_provider is None:
            self._schema_provider = SchemaRegistry()

        if not self._registered:
            if self._register_fn:
                self._register_fn(self._schema_provider)
            self._registered = True

        return self._schema_provider

    @property
    def schema_provider(self) -> SchemaProviderABC | None:
        """Get the current schema provider (may be None if not bootstrapped)."""
        return self._schema_provider

    @property
    def is_registered(self) -> bool:
        """Check if schemas have been registered."""
        return self._registered

    def reset(self) -> None:
        """Reset the bootstrap state (primarily for testing).

        Clears the cached provider and registration state.
        """
        self._schema_provider = None
        self._registered = False


def create_schema_bootstrap_service(
    *,
    schema_provider: SchemaProviderABC | None = None,
    register_fn: Callable[[SchemaProviderABC], Any] | None = None,
    auto_register: bool = False,
) -> SchemaBootstrapService:
    """Create a schema bootstrap service.

    Factory function for creating SchemaBootstrapService instances
    with optional pre-configured schema provider.

    Args:
        schema_provider: Optional pre-existing schema provider to use.
            If not provided, a new SchemaRegistry will be created.
        register_fn: Optional callable to register schemas.
        auto_register: If True, immediately register all schemas.
            Default is False for lazy initialization.

    Returns:
        Configured SchemaBootstrapService instance.
    """
    service = SchemaBootstrapService(
        _schema_provider=schema_provider,
        _register_fn=register_fn,
    )
    if auto_register:
        service.ensure_registered()
    return service


__all__ = [
    "SchemaBootstrapService",
    "create_schema_bootstrap_service",
]
