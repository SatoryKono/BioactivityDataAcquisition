"""Pipeline Registry for discovering and instantiating pipelines.

MOVED to composition layer to fix dependency direction.

This module provides the canonical instance-level ``PipelineRegistry`` for:
- Test isolation (each test can have its own registry)
- Parallel test execution without clear()
- Proper DI through composition root
"""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING, NamedTuple

from bioetl.domain.ports import PipelineFactoryPort

if TYPE_CHECKING:
    import pyarrow as pa

__all__ = [
    "PipelineDefinition",
    "PipelineFactoryPort",
    "PipelineRegistry",
    "create_registry",
    "get_default_registry",
]

_compat_default_registry: PipelineRegistry | None = None


class PipelineDefinition(NamedTuple):
    """Definition of a registered pipeline."""

    factory: PipelineFactoryPort
    """Factory instance."""

    silver_schema: pa.Schema | None
    """PyArrow schema for Silver layer validation."""

    gold_schema: object
    """Pandera schema for Gold layer validation (required)."""

    pandera_silver_schema: object | None = None
    """Pandera DataFrameModel class for Silver layer validation."""


class PipelineRegistry:
    """Registry for pipeline factories.

    Thread-safe instance-level registry for pipeline factory instances.
    All public methods are protected with RLock for concurrent access.

    This class can be instantiated for test isolation or used via the
    default global instance for backward compatibility.

    Example (instance-level for tests):
        >>> registry = PipelineRegistry()
        >>> factory = GenericPipelineFactory(...)
        >>> registry.register_factory(factory)

    Example (backward-compatible class method API):
        >>> factory = GenericPipelineFactory(...)
        >>> PipelineRegistry.register_factory(factory)  # Uses default instance
    """

    def __init__(self) -> None:
        """Initialize a new empty registry."""
        self._registry: dict[str, PipelineDefinition] = {}
        self._lock = threading.RLock()

    def _build_definition(self, factory: PipelineFactoryPort) -> PipelineDefinition:
        """Build the stored pipeline definition after schema validation."""
        gold_schema = getattr(factory, "gold_schema", None)
        if gold_schema is None:
            raise ValueError(
                f"Factory '{factory.pipeline_name}' must have gold_schema. "
                "All Gold layer writes require schema validation."
            )
        return PipelineDefinition(
            factory=factory,
            silver_schema=factory.silver_schema,
            gold_schema=gold_schema,
            pandera_silver_schema=getattr(factory, "pandera_silver_schema", None),
        )

    def register_factory(
        self,
        factory: PipelineFactoryPort,
    ) -> None:
        """Register a pipeline factory instance.

        Thread-safe registration with duplicate detection.

        Args:
            factory: Factory instance with pipeline_name and silver_schema attributes

        Raises:
            ValueError: If factory does not have gold_schema attribute
            ValueError: If pipeline is already registered (prevents double registration)
        """
        self.register(factory.pipeline_name, factory)

    def get(self, pipeline_name: str) -> PipelineDefinition:
        """Get pipeline definition by name.

        Thread-safe read access to registry.

        Args:
            pipeline_name: Pipeline identifier

        Returns:
            PipelineDefinition with factory and schema

        Raises:
            RuntimeError: If registry is empty (registration not called)
            ValueError: If pipeline is not registered
        """
        with self._lock:
            if not self._registry:
                raise RuntimeError(
                    "PipelineRegistry is empty. "
                    "Did you forget to call register_all_pipelines()?"
                )
            if pipeline_name not in self._registry:
                raise ValueError(
                    f"Unknown pipeline name: {pipeline_name}. "
                    f"Available: {sorted(self._registry.keys())}"
                )
            return self._registry[pipeline_name]

    def list_pipelines(self) -> list[str]:
        """List all registered pipeline names.

        Thread-safe listing with deterministic ordering.
        Returns a snapshot of keys sorted alphabetically.

        Returns:
            Sorted list of pipeline names (deterministic order).
        """
        with self._lock:
            return sorted(self._registry.keys())

    def register(
        self,
        key: str,
        value: PipelineFactoryPort,
    ) -> None:
        """Register a pipeline factory (unified API).

        Thread-safe registration with duplicate detection.
        This method provides a unified API consistent with other registries.
        For backward compatibility, use register_factory() which extracts
        the key from factory.pipeline_name.

        Args:
            key: Pipeline name (must match factory.pipeline_name)
            value: Pipeline factory instance

        Raises:
            ValueError: If factory does not have gold_schema attribute
            ValueError: If key does not match factory.pipeline_name
            ValueError: If pipeline is already registered
        """
        if key != value.pipeline_name:
            raise ValueError(
                f"Pipeline key '{key}' does not match "
                f"factory.pipeline_name '{value.pipeline_name}'."
            )
        with self._lock:
            if key in self._registry:
                raise ValueError(
                    f"Pipeline already registered: {key}. "
                    "Use a new registry instance or clear() for tests."
                )
            self._registry[key] = self._build_definition(value)

    def list_keys(self) -> list[str]:
        """List all registered pipeline names (unified API).

        Alias for list_pipelines().

        Returns:
            Collection of keys.
        """
        return self.list_pipelines()

    def contains(self, key: str) -> bool:
        """Check if pipeline is registered.

        Thread-safe check for key existence.

        Args:
            key: Pipeline name to check

        Returns:
            True if pipeline is registered, False otherwise
        """
        with self._lock:
            return key in self._registry

    def clear(self) -> None:
        """Clear all registrations (for testing).

        Thread-safe reset of registry state.
        WARNING: Only use in tests. Not for production.
        """
        with self._lock:
            self._registry.clear()


def create_registry() -> PipelineRegistry:
    """Create a new isolated registry instance.

    Use this for test isolation or when you need multiple registries
    in the same process.

    Returns:
        A new empty PipelineRegistry instance.
    """
    return PipelineRegistry()


def get_default_registry() -> PipelineRegistry:
    """Return the retained compatibility registry instance.

    Canonical runtime/bootstrap assembly should prefer explicit registries via
    ``create_registry()`` and ``register_all_pipelines(registry=...)``. This
    helper remains for compatibility-oriented tests and narrow public facade
    coverage that still exercise the historical default-registry seam.
    """
    global _compat_default_registry
    if _compat_default_registry is None:
        _compat_default_registry = create_registry()
        _compat_default_registry._bioetl_shared_default_registry = True
    return _compat_default_registry
