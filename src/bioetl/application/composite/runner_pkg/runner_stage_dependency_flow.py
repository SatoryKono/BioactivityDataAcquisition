"""Dependency-stage helpers for composite runner orchestration."""

from __future__ import annotations

from collections.abc import Callable

import polars as pl

from bioetl.application.composite.checkpoint import CompositeCheckpointState
from bioetl.application.composite.dependency_coordinator import (
    DependencyCoordinatorService,
)
from bioetl.application.composite.runner_pkg.runner_stage_types import (
    _CompositeRunnerStageHostProtocol,
    _DependencyPhaseOutcome,
    _PreparedDependenciesRunContext,
)
from bioetl.application.runtime_clock import resolve_runtime_clock
from bioetl.domain.composite.result import DependencyResult
from bioetl.domain.exceptions import InvalidStateError
from bioetl.domain.ports import ExecutionMetricsRunnerPort

__all__ = [
    "build_dependencies_run_context",
    "build_dependency_phase_outcome",
    "collect_successful_dependencies",
    "validate_dependency_preconditions",
]


def build_dependencies_run_context(
    host: _CompositeRunnerStageHostProtocol,
) -> _PreparedDependenciesRunContext:
    """Resolve dependency runtime collaborators and pipeline names for execution."""
    coordinator, runner_factory = validate_dependency_preconditions(host)
    dependency_pipeline_names = [
        dependency.pipeline for dependency in host._config.dependencies
    ]
    return _PreparedDependenciesRunContext(
        coordinator=coordinator,
        runner_factory=runner_factory,
        dependency_pipeline_names=dependency_pipeline_names,
    )


def build_dependency_phase_outcome(
    host: _CompositeRunnerStageHostProtocol,
    dependency_results: dict[str, DependencyResult],
) -> _DependencyPhaseOutcome:
    """Normalize dependency results into a reusable finalization context."""
    required_failed = host._find_required_failures(dependency_results)
    succeeded, failed = host._summarize_dependency_outcomes(dependency_results)
    return _DependencyPhaseOutcome(
        dependency_results=dependency_results,
        required_failed=required_failed,
        succeeded=succeeded,
        failed=failed,
    )


def validate_dependency_preconditions(
    host: _CompositeRunnerStageHostProtocol,
) -> tuple[
    DependencyCoordinatorService,
    Callable[[str, pl.DataFrame], ExecutionMetricsRunnerPort],
]:
    """Validate that dependency coordinator and runner factory are available."""
    coordinator = host._dependency_coordinator
    runner_factory = host._dependencies_runner_factory
    if coordinator is None or runner_factory is None:
        raise InvalidStateError(
            "Dependency coordinator and runner factory must be set "
            "when dependencies are configured"
        )
    return coordinator, runner_factory


def collect_successful_dependencies(
    host: _CompositeRunnerStageHostProtocol,
    state: CompositeCheckpointState,
    dependency_results: dict[str, DependencyResult],
) -> CompositeCheckpointState:
    """Mark each successful dependency as completed on checkpoint state."""
    clock = resolve_runtime_clock(getattr(host, "_clock", None))
    for dep_name, dep_result in dependency_results.items():
        if dep_result.is_success:
            state = state.with_dependency_completed(
                dep_name,
                dep_result,
                clock=clock,
            )
    return state
