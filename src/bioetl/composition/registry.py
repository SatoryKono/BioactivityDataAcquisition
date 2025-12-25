"""Pipeline Registry for discovering and instantiating pipelines.

MOVED to composition layer to fix dependency direction.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar, NamedTuple, Protocol, runtime_checkable

import pyarrow as pa

if TYPE_CHECKING:
    from bioetl.application.core.base import BasePipeline
    from bioetl.application.core.runner import PipelineRunner
    from bioetl.composition.observability import ObservabilityBundle
    from bioetl.domain.config import RuntimeConfig
    from bioetl.domain.filter_config import InputFilterConfig
    from bioetl.domain.ports import LoggerPort
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
        **kwargs: Any,
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

    Example:
        >>> factory = GenericPipelineFactory(...)
        >>> PipelineRegistry.register_factory(factory)
    """

    _registry: ClassVar[dict[str, PipelineDefinition]] = {}

    @classmethod
    def register_factory(
        cls,
        factory: PipelineFactoryProtocol,
    ) -> None:
        """Register a pipeline factory instance.

        Args:
            factory: Factory instance with pipeline_name and silver_schema attributes

        Raises:
            ValueError: If factory does not have gold_schema attribute
        """
        gold_schema = getattr(factory, "gold_schema", None)
        if gold_schema is None:
            raise ValueError(
                f"Factory '{factory.pipeline_name}' must have gold_schema. "
                "All Gold layer writes require schema validation."
            )

        cls._registry[factory.pipeline_name] = PipelineDefinition(
            factory=factory,
            silver_schema=factory.silver_schema,
            gold_schema=gold_schema,
        )

    @classmethod
    def get(cls, pipeline_name: str) -> PipelineDefinition:
        """Get pipeline definition by name.

        Args:
            pipeline_name: Pipeline identifier

        Returns:
            PipelineDefinition with factory and schema

        Raises:
            RuntimeError: If registry is empty (registration not called)
            ValueError: If pipeline is not registered
        """
        if not cls._registry:
            raise RuntimeError(
                "PipelineRegistry is empty. "
                "Did you forget to call register_all_pipelines()?"
            )
        if pipeline_name not in cls._registry:
            raise ValueError(
                f"Unknown pipeline name: {pipeline_name}. "
                f"Available: {list(cls._registry.keys())}"
            )
        return cls._registry[pipeline_name]

    @classmethod
    def list_pipelines(cls) -> list[str]:
        """List all registered pipeline names.

        Legacy alias for list_keys().
        """
        return list(cls._registry.keys())

    @classmethod
    def register(
        cls,
        key: str,
        value: PipelineFactoryProtocol,
    ) -> None:
        """Register a pipeline factory (unified API).

        This method provides a unified API consistent with other registries.
        For backward compatibility, use register_factory() which extracts
        the key from factory.pipeline_name.

        Args:
            key: Pipeline name (must match factory.pipeline_name)
            value: Pipeline factory instance

        Raises:
            ValueError: If factory does not have gold_schema attribute
        """
        gold_schema = getattr(value, "gold_schema", None)
        if gold_schema is None:
            raise ValueError(
                f"Factory '{key}' must have gold_schema. "
                "All Gold layer writes require schema validation."
            )
        cls._registry[key] = PipelineDefinition(
            factory=value,
            silver_schema=value.silver_schema,
            gold_schema=gold_schema,
        )

    @classmethod
    def list_keys(cls) -> list[str]:
        """List all registered pipeline names (unified API).

        Alias for list_pipelines().
        """
        return cls.list_pipelines()

    @classmethod
    def contains(cls, key: str) -> bool:
        """Check if pipeline is registered.

        Args:
            key: Pipeline name to check

        Returns:
            True if pipeline is registered, False otherwise
        """
        return key in cls._registry

    @classmethod
    def clear(cls) -> None:
        """Clear all registrations (for testing).

        WARNING: Only use in tests. Not for production.
        """
        cls._registry.clear()
