"""Dependency completion helpers for CompositePipelineRunner."""

from __future__ import annotations

from collections.abc import Callable

import polars as pl

from bioetl.application.composite.checkpoint import (
    CompositeCheckpointState,
)
from bioetl.application.composite.dependency_coordinator import (
    DependencyCoordinatorService,
)
from bioetl.application.composite.runner_pkg.runner_stage_dependency_flow import (
    build_dependency_phase_outcome,
    collect_successful_dependencies,
    validate_dependency_preconditions,
)
from bioetl.application.composite.runner_pkg.runner_stage_dependency_state_flow import (
    complete_dependencies_phase,
    handle_dependencies_phase_exception,
)
from bioetl.application.composite.runner_pkg.runner_stage_types import (
    _CompositeRunnerStageHostProtocol,
    _DependencyPhaseOutcome,
)
from bioetl.domain.composite.result import (
    DependencyResult,
)
from bioetl.domain.exceptions import InvalidStateError
from bioetl.domain.ports import ExecutionMetricsRunnerPort

__all__ = ["_CompositeRunnerStageCompletionMixin"]


class _CompositeRunnerStageCompletionMixin:
    """Dependency postprocessing and phase completion for stage orchestration."""

    async def _postprocess_dependency_results(
        self: _CompositeRunnerStageHostProtocol,
        state: CompositeCheckpointState,
        dependency_results: dict[str, DependencyResult],
    ) -> tuple[CompositeCheckpointState, dict[str, DependencyResult]]:
        """Record successful dependencies and finalize the dependency phase."""
        state = self._collect_successful_dependencies(state, dependency_results)
        outcome = self._build_dependency_phase_outcome(dependency_results)
        return await self._finalize_dependencies_phase(state, outcome)

    def _build_dependency_phase_outcome(
        self: _CompositeRunnerStageHostProtocol,
        dependency_results: dict[str, DependencyResult],
    ) -> _DependencyPhaseOutcome:
        """Normalize dependency results into a reusable finalization context."""
        return build_dependency_phase_outcome(self, dependency_results)

    def _validate_dependency_preconditions(
        self: _CompositeRunnerStageHostProtocol,
    ) -> tuple[
        DependencyCoordinatorService,
        Callable[[str, pl.DataFrame], ExecutionMetricsRunnerPort],
    ]:
        """Validate that dependency coordinator and runner factory are available."""
        return validate_dependency_preconditions(self)

    def _collect_successful_dependencies(
        self: _CompositeRunnerStageHostProtocol,
        state: CompositeCheckpointState,
        dependency_results: dict[str, DependencyResult],
    ) -> CompositeCheckpointState:
        """Mark each successful dependency as completed on checkpoint state."""
        return collect_successful_dependencies(self, state, dependency_results)

    async def _finalize_dependencies_phase(
        self: _CompositeRunnerStageHostProtocol,
        state: CompositeCheckpointState,
        outcome: _DependencyPhaseOutcome,
    ) -> tuple[CompositeCheckpointState, dict[str, DependencyResult]]:
        """Check for required failures and complete the dependencies phase."""
        if outcome.required_failed:
            message = f"Required dependencies failed: {outcome.required_failed}"
            await self._persist_failed_state(
                state,
                stage="dependencies_failed",
                error=message,
            )
            raise InvalidStateError(message)

        completed_state = await self._complete_dependencies_phase(
            state,
            succeeded=outcome.succeeded,
            failed=outcome.failed,
        )
        self._record_dependencies_stage_completed(outcome.dependency_results)
        return completed_state, outcome.dependency_results

    async def _complete_dependencies_phase(
        self: _CompositeRunnerStageHostProtocol,
        state: CompositeCheckpointState,
        *,
        succeeded: int,
        failed: int,
    ) -> CompositeCheckpointState:
        """Transition to DEPENDENCIES_COMPLETED, log, and persist checkpoint."""
        return await complete_dependencies_phase(
            self,
            state,
            succeeded=succeeded,
            failed=failed,
        )

    async def _handle_dependencies_phase_exception(
        self: _CompositeRunnerStageHostProtocol,
        state: CompositeCheckpointState,
        error: Exception,
    ) -> None:
        """Log dependency-phase failure and persist FAILED checkpoint."""
        await handle_dependencies_phase_exception(self, state, error)
