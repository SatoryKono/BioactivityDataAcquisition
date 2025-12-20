"""Pipeline Registry for discovering and instantiating pipelines.

Supports both class-based factories (legacy) and instance-based factories (new).
"""

from typing import Any, NamedTuple, Protocol, runtime_checkable

import pyarrow as pa


@runtime_checkable
class PipelineFactoryProtocol(Protocol):
    """Protocol for pipeline factories.

    Supports both class-based (old) and instance-based (new) factories.
    """

    pipeline_name: str
    silver_schema: pa.Schema | None

    def create_with_services(self, runtime: Any, settings: Any, logger: Any, **kwargs: Any) -> Any:
        """Create pipeline with services."""
        ...


class PipelineDefinition(NamedTuple):
    """Definition of a registered pipeline."""

    factory: type[Any] | PipelineFactoryProtocol
    """Factory class or instance."""

    silver_schema: pa.Schema | None
    """PyArrow schema for Silver layer validation."""

    gold_schema: Any | None = None
    """Pandera schema for Gold layer validation."""

    is_instance: bool = False
    """True if factory is an instance, False if it's a class."""


class PipelineRegistry:
    """Registry for pipeline factories.

    Supports two registration patterns:
    1. Class-based (legacy): register(name, FactoryClass, schema)
    2. Instance-based (new): register_factory(factory_instance)

    Example (legacy):
        >>> PipelineRegistry.register("my_pipeline", MyPipelineFactory, MY_SCHEMA)

    Example (new):
        >>> factory = GenericPipelineFactory(...)
        >>> PipelineRegistry.register_factory(factory)
    """

    _registry: dict[str, PipelineDefinition] = {}

    @classmethod
    def register(
        cls,
        pipeline_name: str,
        factory: type[Any],
        silver_schema: pa.Schema | None = None,
        gold_schema: Any | None = None,
    ) -> None:
        """Register a class-based pipeline factory (legacy pattern).

        Args:
            pipeline_name: Unique pipeline identifier
            factory: Factory class (must have create_with_services classmethod)
            silver_schema: Optional PyArrow schema for Silver layer
            gold_schema: Optional Pandera schema for Gold layer
        """
        cls._registry[pipeline_name] = PipelineDefinition(
            factory=factory,
            silver_schema=silver_schema,
            gold_schema=gold_schema,
            is_instance=False,
        )

    @classmethod
    def register_factory(
        cls,
        factory: PipelineFactoryProtocol,
    ) -> None:
        """Register an instance-based pipeline factory (new pattern).

        Args:
            factory: Factory instance with pipeline_name and silver_schema attributes
        """
        # Try to get gold_schema from factory if available, else None
        gold_schema = getattr(factory, "gold_schema", None)

        cls._registry[factory.pipeline_name] = PipelineDefinition(
            factory=factory,
            silver_schema=factory.silver_schema,
            gold_schema=gold_schema,
            is_instance=True,
        )

    @classmethod
    def get(cls, pipeline_name: str) -> PipelineDefinition:
        """Get pipeline definition by name.

        Args:
            pipeline_name: Pipeline identifier

        Returns:
            PipelineDefinition with factory and schema

        Raises:
            ValueError: If pipeline is not registered
        """
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
