"""Core pipeline registry types used by composition public facades."""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING, NamedTuple

from bioetl.domain.ports import PipelineFactoryPort

if TYPE_CHECKING:
    import pyarrow as pa

__all__ = [
    "PipelineDefinition",
    "PipelineRegistry",
    "create_registry",
    "get_default_registry",
]


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
    """Registry for pipeline factories."""

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

    def register_factory(self, factory: PipelineFactoryPort) -> None:
        """Register a pipeline factory instance."""
        self.register(factory.pipeline_name, factory)

    def get(self, pipeline_name: str) -> PipelineDefinition:
        """Get pipeline definition by name."""
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
        """List all registered pipeline names."""
        with self._lock:
            return sorted(self._registry.keys())

    def register(self, key: str, value: PipelineFactoryPort) -> None:
        """Register a pipeline factory."""
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
        """List all registered pipeline names."""
        return self.list_pipelines()

    def contains(self, key: str) -> bool:
        """Check if pipeline is registered."""
        with self._lock:
            return key in self._registry

    def clear(self) -> None:
        """Clear all registrations for testing."""
        with self._lock:
            self._registry.clear()


def create_registry() -> PipelineRegistry:
    """Create a new isolated registry instance."""
    return PipelineRegistry()


_compat_default_registry: PipelineRegistry | None = None


def get_default_registry() -> PipelineRegistry:
    """Return the retained compatibility registry instance."""
    global _compat_default_registry
    if _compat_default_registry is None:
        _compat_default_registry = create_registry()
        _compat_default_registry._bioetl_shared_default_registry = True
    return _compat_default_registry
