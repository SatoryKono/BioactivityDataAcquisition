"""DAG validation helpers for declarative workflow configuration."""

from __future__ import annotations

from collections import Counter, deque
from collections.abc import Iterable, Sequence
from typing import Protocol

__all__ = [
    "WorkflowDagValidationError",
    "topologically_sorted_step_ids",
    "validate_workflow_dag",
]


class _WorkflowStepLike(Protocol):
    """Minimal workflow-step contract needed for DAG validation."""

    step_id: str
    depends_on: tuple[str, ...]


class WorkflowDagValidationError(ValueError):
    """Raised when workflow dependency graph invariants are violated."""


def validate_workflow_dag(steps: Iterable[_WorkflowStepLike]) -> None:
    """Validate duplicate IDs, missing dependencies, and dependency cycles."""
    topologically_sorted_step_ids(tuple(steps))


def topologically_sorted_step_ids(
    steps: Sequence[_WorkflowStepLike],
) -> tuple[str, ...]:
    """Return workflow step IDs in dependency order.

    Raises:
        WorkflowDagValidationError: When the workflow contains duplicate step
            IDs, references unknown dependencies, or contains a dependency cycle.
    """
    if not steps:
        raise WorkflowDagValidationError("Workflow must define at least one step")

    step_ids = [step.step_id for step in steps]
    duplicates = sorted(step_id for step_id, count in Counter(step_ids).items() if count > 1)
    if duplicates:
        duplicate_list = ", ".join(duplicates)
        raise WorkflowDagValidationError(
            f"Workflow defines duplicate step_id values: {duplicate_list}"
        )

    known_steps = set(step_ids)
    missing_dependencies: list[str] = []
    for step in steps:
        for dependency in step.depends_on:
            if dependency not in known_steps:
                missing_dependencies.append(f"{step.step_id} -> {dependency}")
    if missing_dependencies:
        missing_list = ", ".join(sorted(missing_dependencies))
        raise WorkflowDagValidationError(
            "Workflow references unknown dependencies: "
            f"{missing_list}. Declare the missing step or fix depends_on."
        )

    incoming_counts: dict[str, int] = {step.step_id: 0 for step in steps}
    outgoing_edges: dict[str, list[str]] = {
        step.step_id: [] for step in steps
    }
    for step in steps:
        for dependency in step.depends_on:
            incoming_counts[step.step_id] += 1
            outgoing_edges[dependency].append(step.step_id)

    ready = deque(sorted(step_id for step_id, count in incoming_counts.items() if count == 0))
    ordered: list[str] = []

    while ready:
        step_id = ready.popleft()
        ordered.append(step_id)
        for dependant in sorted(outgoing_edges[step_id]):
            incoming_counts[dependant] -= 1
            if incoming_counts[dependant] == 0:
                ready.append(dependant)

    if len(ordered) != len(steps):
        cycle_nodes = sorted(
            step_id for step_id, count in incoming_counts.items() if count > 0
        )
        cycle_list = ", ".join(cycle_nodes)
        raise WorkflowDagValidationError(
            "Workflow dependency cycle detected among steps: "
            f"{cycle_list}. Remove the cycle from depends_on."
        )

    return tuple(ordered)
