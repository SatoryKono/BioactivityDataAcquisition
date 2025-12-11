"""Stage registry for pipeline composition.

This module provides a registry pattern for managing pipeline stages,
enabling flexible composition and ordering of ETL stages.

The registry pattern decouples stage definitions from the pipeline
execution logic, making it easier to add, remove, or reorder stages.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterator
from typing import TYPE_CHECKING, Any, Generic, TypeVar

if TYPE_CHECKING:
    from bioetl.application.pipelines.context import PipelineRuntimeContext

T = TypeVar("T")


class StageABC(ABC, Generic[T]):
    """Abstract base for pipeline stages.

    Each stage represents a discrete unit of work in the ETL pipeline.
    Stages are composable and can be registered with a StageRegistry.

    Type parameter T represents the data type passed between stages.

    Example:
        >>> class ExtractStage(StageABC[pd.DataFrame]):
        ...     @property
        ...     def name(self) -> str:
        ...         return "extract"
        ...
        ...     def execute(self, context, data):
        ...         # Extract logic here
        ...         return extracted_data
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Stage name for logging and metrics.

        Returns:
            Unique identifier for this stage.
        """
        ...

    @property
    def order(self) -> int:
        """Execution order (lower numbers execute first).

        Returns:
            Integer order value (default: 0).
        """
        return 0

    @property
    def skip_on_dry_run(self) -> bool:
        """Whether to skip this stage during dry runs.

        Returns:
            True if stage should be skipped in dry run mode.
        """
        return False

    @abstractmethod
    def execute(
        self,
        context: "PipelineRuntimeContext",
        data: T | None,
    ) -> T:
        """Execute stage logic.

        Args:
            context: Runtime context with logging, metrics, and state.
            data: Input data from previous stage (None for first stage).

        Returns:
            Output data to pass to next stage.

        Raises:
            StageExecutionError: If stage execution fails.
        """
        ...


class StageRegistry:
    """Registry of pipeline stages.

    Manages a collection of stages and provides iteration in execution order.
    Stages are stored by name and can be retrieved, replaced, or removed.

    Example:
        >>> registry = StageRegistry()
        >>> registry.register(ExtractStage())
        >>> registry.register(TransformStage())
        >>> for stage in registry.all():
        ...     result = stage.execute(context, data)
    """

    def __init__(self) -> None:
        """Initialize empty registry."""
        self._stages: dict[str, StageABC[Any]] = {}

    def register(self, stage: StageABC[Any]) -> None:
        """Register a stage.

        Args:
            stage: Stage instance to register.

        Note:
            If a stage with the same name exists, it will be replaced.
        """
        self._stages[stage.name] = stage

    def unregister(self, name: str) -> StageABC[Any] | None:
        """Remove a stage by name.

        Args:
            name: Stage name to remove.

        Returns:
            Removed stage or None if not found.
        """
        return self._stages.pop(name, None)

    def get(self, name: str) -> StageABC[Any] | None:
        """Get stage by name.

        Args:
            name: Stage name to retrieve.

        Returns:
            Stage instance or None if not found.
        """
        return self._stages.get(name)

    def has(self, name: str) -> bool:
        """Check if stage is registered.

        Args:
            name: Stage name to check.

        Returns:
            True if stage is registered.
        """
        return name in self._stages

    def all(self) -> list[StageABC[Any]]:
        """Get all stages in execution order.

        Returns:
            List of stages sorted by order property.
        """
        return sorted(self._stages.values(), key=lambda s: s.order)

    def names(self) -> list[str]:
        """Get all registered stage names.

        Returns:
            List of stage names in registration order.
        """
        return list(self._stages.keys())

    def __len__(self) -> int:
        """Return number of registered stages."""
        return len(self._stages)

    def __iter__(self) -> Iterator[StageABC[Any]]:
        """Iterate over stages in execution order."""
        return iter(self.all())


class StageExecutionError(Exception):
    """Error raised when stage execution fails."""

    def __init__(
        self,
        stage_name: str,
        message: str,
        cause: Exception | None = None,
    ) -> None:
        """Initialize stage execution error.

        Args:
            stage_name: Name of the failed stage.
            message: Error description.
            cause: Original exception that caused the failure.
        """
        super().__init__(f"Stage '{stage_name}' failed: {message}")
        self.stage_name = stage_name
        self.cause = cause


__all__ = [
    "StageABC",
    "StageExecutionError",
    "StageRegistry",
]
