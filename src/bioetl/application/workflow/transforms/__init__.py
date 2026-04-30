"""Transform registry primitives for declarative workflow execution."""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass, field

from bioetl.domain.workflow import WorkflowTransformSpec

type WorkflowTransformOutput = object
type WorkflowTransformCallable = Callable[
    [WorkflowTransformSpec, Mapping[str, object]],
    WorkflowTransformOutput | Awaitable[WorkflowTransformOutput],
]

__all__ = [
    "WorkflowTransformCallable",
    "WorkflowTransformOutput",
    "WorkflowTransformRegistry",
]


@dataclass(slots=True)
class WorkflowTransformRegistry:
    """In-memory registry for named workflow transform executors."""

    _executors: dict[str, WorkflowTransformCallable] = field(default_factory=dict)

    def register(
        self,
        transform_name: str,
        executor: WorkflowTransformCallable,
    ) -> None:
        """Register or replace an executor for a declarative transform name."""
        self._executors[transform_name] = executor

    def get(self, transform_name: str) -> WorkflowTransformCallable:
        """Return a registered executor or fail with a bounded error."""
        try:
            return self._executors[transform_name]
        except KeyError as exc:
            raise KeyError(f"Unknown workflow transform: {transform_name}") from exc

    def contains(self, transform_name: str) -> bool:
        """Return whether an executor is registered for the transform name."""
        return transform_name in self._executors
