"""Pipeline Registry for discovering and instantiating pipelines.

MOVED to composition layer to fix dependency direction.
"""

from typing import Any, ClassVar, NamedTuple, Protocol, runtime_checkable

import pyarrow as pa


@runtime_checkable
class PipelineFactoryProtocol(Protocol):
    """Protocol for pipeline factories."""

    pipeline_name: str
    silver_schema: pa.Schema | None

    def create_with_services(
        self, runtime: Any, settings: Any, logger: Any, **kwargs: Any
    ) -> Any:
        """Create pipeline with services."""
        ...


class PipelineDefinition(NamedTuple):
    """Definition of a registered pipeline."""

    factory: PipelineFactoryProtocol
    """Factory instance."""

    silver_schema: pa.Schema | None
    """PyArrow schema for Silver layer validation."""

    gold_schema: Any | None = None
    """Pandera schema for Gold layer validation."""


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
        """
        gold_schema = getattr(factory, "gold_schema", None)

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
        """List all registered pipeline names."""
        return list(cls._registry.keys())
