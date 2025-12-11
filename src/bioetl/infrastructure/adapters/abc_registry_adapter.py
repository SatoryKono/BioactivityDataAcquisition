"""Infrastructure adapter for ABC registry resolver port.

This module provides a concrete implementation of the ABC registry
resolver port using the infrastructure layer's YAML-based registry.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from bioetl.application.ports.infrastructure_factory_port import (
    ABCRegistryResolverPortABC,
)


class ABCRegistryResolverAdapter(ABCRegistryResolverPortABC):
    """Adapter implementing ABC registry resolver port.

    This adapter wraps the infrastructure's ABCRegistryResolver,
    providing a clean interface that conforms to the application port.
    """

    def __init__(
        self,
        additional_impls_paths: list[Path] | None = None,
    ) -> None:
        """Initialize adapter with optional additional implementation paths.

        Args:
            additional_impls_paths: Additional YAML files with ABC implementations.
        """
        self._additional_paths = additional_impls_paths or []
        self._resolver: Any = None

    def _get_resolver(self) -> Any:
        """Lazily create the underlying resolver."""
        if self._resolver is None:
            from bioetl.infrastructure.clients.base.abc_registry_resolver import (
                ABCRegistryResolver,
            )

            self._resolver = ABCRegistryResolver(
                additional_impls_paths=self._additional_paths
            )
        return self._resolver

    def resolve(self, abc_name: str) -> type:
        """Resolve implementation class for given ABC name."""
        resolver = self._get_resolver()
        return resolver.resolve(abc_name)

    def resolve_instance(self, abc_name: str, **kwargs: Any) -> object:
        """Resolve and instantiate implementation for given ABC name."""
        resolver = self._get_resolver()
        impl_class = resolver.resolve(abc_name)
        return impl_class(**kwargs)

    def resolve_default_factory(self, abc_name: str) -> Any:
        """Resolve default factory function for given ABC name."""
        resolver = self._get_resolver()
        return resolver.resolve_default_factory(abc_name)


__all__ = ["ABCRegistryResolverAdapter"]
