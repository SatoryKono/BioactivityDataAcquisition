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
    _assert_workflow_has_steps(steps)
    step_ids = [step.step_id for step in steps]
    _raise_on_duplicate_step_ids(step_ids)
    _raise_on_missing_dependencies(steps, known_steps=set(step_ids))
    incoming_counts, outgoing_edges = _build_dependency_graph(steps)
    ordered = _topological_sort(incoming_counts, outgoing_edges)
    _raise_on_dependency_cycle(steps, ordered, incoming_counts)
    return tuple(ordered)


def _assert_workflow_has_steps(steps: Sequence[_WorkflowStepLike]) -> None:
    """Reject an empty workflow definition."""
    if steps:
        return
    raise WorkflowDagValidationError("Workflow must define at least one step")


def _raise_on_duplicate_step_ids(step_ids: Sequence[str]) -> None:
    """Reject workflows that define the same step ID more than once."""
    duplicates = sorted(
        step_id for step_id, count in Counter(step_ids).items() if count > 1
    )
    if not duplicates:
        return
    duplicate_list = ", ".join(duplicates)
    raise WorkflowDagValidationError(
        f"Workflow defines duplicate step_id values: {duplicate_list}"
    )


def _raise_on_missing_dependencies(
    steps: Sequence[_WorkflowStepLike],
    *,
    known_steps: set[str],
) -> None:
    """Reject workflows that reference undeclared dependencies."""
    missing_dependencies = _collect_missing_dependencies(steps, known_steps=known_steps)
    if not missing_dependencies:
        return
    missing_list = ", ".join(sorted(missing_dependencies))
    raise WorkflowDagValidationError(
        "Workflow references unknown dependencies: "
        f"{missing_list}. Declare the missing step or fix depends_on."
    )


def _collect_missing_dependencies(
    steps: Sequence[_WorkflowStepLike],
    *,
    known_steps: set[str],
) -> list[str]:
    """Collect step->dependency references that point at unknown steps."""
    missing_dependencies: list[str] = []
    for step in steps:
        for dependency in step.depends_on:
            if dependency not in known_steps:
                missing_dependencies.append(f"{step.step_id} -> {dependency}")
    return missing_dependencies


def _build_dependency_graph(
    steps: Sequence[_WorkflowStepLike],
) -> tuple[dict[str, int], dict[str, list[str]]]:
    """Build incoming-edge counts and outgoing-edge adjacency lists."""
    incoming_counts: dict[str, int] = {step.step_id: 0 for step in steps}
    outgoing_edges: dict[str, list[str]] = {step.step_id: [] for step in steps}
    for step in steps:
        for dependency in step.depends_on:
            incoming_counts[step.step_id] += 1
            outgoing_edges[dependency].append(step.step_id)
    return incoming_counts, outgoing_edges


def _topological_sort(
    incoming_counts: dict[str, int],
    outgoing_edges: dict[str, list[str]],
) -> list[str]:
    """Return step IDs in topological order for an already validated graph."""
    ready = deque(
        sorted(step_id for step_id, count in incoming_counts.items() if count == 0)
    )
    ordered: list[str] = []
    while ready:
        step_id = ready.popleft()
        ordered.append(step_id)
        _mark_dependants_ready(step_id, ready, incoming_counts, outgoing_edges)
    return ordered


def _mark_dependants_ready(
    step_id: str,
    ready: deque[str],
    incoming_counts: dict[str, int],
    outgoing_edges: dict[str, list[str]],
) -> None:
    """Decrement dependency counts for the dependants of one ready node."""
    for dependant in sorted(outgoing_edges[step_id]):
        incoming_counts[dependant] -= 1
        if incoming_counts[dependant] == 0:
            ready.append(dependant)


def _raise_on_dependency_cycle(
    steps: Sequence[_WorkflowStepLike],
    ordered: Sequence[str],
    incoming_counts: dict[str, int],
) -> None:
    """Reject workflows whose dependency graph still has residual edges."""
    if len(ordered) == len(steps):
        return
    cycle_nodes = sorted(
        step_id for step_id, count in incoming_counts.items() if count > 0
    )
    cycle_list = ", ".join(cycle_nodes)
    raise WorkflowDagValidationError(
        "Workflow dependency cycle detected among steps: "
        f"{cycle_list}. Remove the cycle from depends_on."
    )
