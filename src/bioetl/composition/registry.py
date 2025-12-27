"""Pipeline Registry for discovering and instantiating pipelines.

MOVED to composition layer to fix dependency direction.

This module provides an instance-level PipelineRegistry for:
- Test isolation (each test can have its own registry)
- Parallel test execution without clear()
- Proper DI through composition root

A default global instance is provided for backward compatibility.
"""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING, Any, NamedTuple, Protocol, runtime_checkable

import pyarrow as pa

if TYPE_CHECKING:
    from bioetl.application.core.base import BasePipeline
    from bioetl.application.core.runner import PipelineRunner
    from bioetl.composition.observability import ObservabilityBundle
    from bioetl.domain.config import RuntimeConfig
    from bioetl.domain.filter_config import InputFilterConfig
    from bioetl.domain.ports import DQMonitorPort, LoggerPort, MetricsPort, TracingPort
    from bioetl.domain.types import RunID
    from bioetl.infrastructure.config import Settings
    from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig


@runtime_checkable
class PipelineFactoryProtocol(Protocol):
    """Protocol for pipeline factories."""

    pipeline_name: str
    silver_schema: pa.Schema | None

    def create_with_services(
        self,
        run_id: RunID,
        runtime: RuntimeConfig,
        settings: Settings,
        logger: LoggerPort,
        config: PipelineYamlConfig | None = ...,
        filter_config: InputFilterConfig | None = ...,
        tracer: TracingPort | None = ...,
        dq_monitor: DQMonitorPort | None = ...,
        metrics: MetricsPort | None = ...,
    ) -> BasePipeline:
        """Create pipeline with services."""
        ...

    def create_runner(
        self,
        run_id: RunID,
        runtime: RuntimeConfig,
        settings: Settings,
        observability: ObservabilityBundle,
        filter_config: InputFilterConfig | None = None,
        config: PipelineYamlConfig | None = None,
    ) -> PipelineRunner:
        """Create pipeline runner."""
        ...


class PipelineDefinition(NamedTuple):
    """Definition of a registered pipeline."""

    factory: PipelineFactoryProtocol
    """Factory instance."""

    silver_schema: pa.Schema | None
    """PyArrow schema for Silver layer validation."""

    gold_schema: Any
    """Pandera schema for Gold layer validation (required)."""


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

    def register_factory(
        self,
        factory: PipelineFactoryProtocol,
    ) -> None:
        """Register a pipeline factory instance.

        Thread-safe registration with duplicate detection.

        Args:
            factory: Factory instance with pipeline_name and silver_schema attributes

        Raises:
            ValueError: If factory does not have gold_schema attribute
            ValueError: If pipeline is already registered (prevents double registration)
        """
        gold_schema = getattr(factory, "gold_schema", None)
        if gold_schema is None:
            raise ValueError(
                f"Factory '{factory.pipeline_name}' must have gold_schema. "
                "All Gold layer writes require schema validation."
            )

        with self._lock:
            if factory.pipeline_name in self._registry:
                raise ValueError(
                    f"Pipeline already registered: {factory.pipeline_name}. "
                    "Use a new registry instance or clear() for tests."
                )
            self._registry[factory.pipeline_name] = PipelineDefinition(
                factory=factory,
                silver_schema=factory.silver_schema,
                gold_schema=gold_schema,
            )

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
        value: PipelineFactoryProtocol,
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
            ValueError: If pipeline is already registered
        """
        gold_schema = getattr(value, "gold_schema", None)
        if gold_schema is None:
            raise ValueError(
                f"Factory '{key}' must have gold_schema. "
                "All Gold layer writes require schema validation."
            )
        with self._lock:
            if key in self._registry:
                raise ValueError(
                    f"Pipeline already registered: {key}. "
                    "Use a new registry instance or clear() for tests."
                )
            self._registry[key] = PipelineDefinition(
                factory=value,
                silver_schema=value.silver_schema,
                gold_schema=gold_schema,
            )

    def list_keys(self) -> list[str]:
        """List all registered pipeline names (unified API).

        Alias for list_pipelines().
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


# Default global instance for backward compatibility
_default_registry = PipelineRegistry()


def get_default_registry() -> PipelineRegistry:
    """Get the default global registry instance.

    Use this function when you need access to the shared registry.
    For tests, prefer creating a new PipelineRegistry() instance.

    Returns:
        The default global PipelineRegistry instance.
    """
    return _default_registry


def create_registry() -> PipelineRegistry:
    """Create a new isolated registry instance.

    Use this for test isolation or when you need multiple registries
    in the same process.

    Returns:
        A new empty PipelineRegistry instance.
    """
    return PipelineRegistry()
