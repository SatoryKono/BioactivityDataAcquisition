"""Stage execution helpers for CompositePipelineRunner."""

from __future__ import annotations

import asyncio
from collections.abc import Callable

import polars as pl

from bioetl.application.composite.checkpoint import (
    CompositeCheckpointState,
    apply_recovery_checkpoint_transition,
)
from bioetl.application.composite.dependency_coordinator import (
    DependencyCoordinatorService,
)
from bioetl.application.composite.runner_pkg.runner_constants import (
    PIPELINE_EXECUTION_ERRORS,
)
from bioetl.application.composite.runner_pkg.runner_stage_dependency_flow import (
    build_dependencies_run_context,
    build_dependency_phase_outcome,
    collect_successful_dependencies,
    validate_dependency_preconditions,
)
from bioetl.application.composite.runner_pkg.runner_stage_dependency_state_flow import (
    complete_dependencies_phase,
    handle_dependencies_phase_exception,
    start_dependencies_phase,
)
from bioetl.application.composite.runner_pkg.runner_stage_enrichment_mixin import (
    _CompositeRunnerStageEnrichmentMixin,
)
from bioetl.application.composite.runner_pkg.runner_stage_support_mixin import (
    _CompositeRunnerStageSupportMixin,
)
from bioetl.application.composite.runner_pkg.runner_stage_types import (
    _CompositeRunnerStageHostProtocol,
    _DependencyPhaseOutcome,
    _PreparedDependenciesRunContext,
)
from bioetl.domain.composite.result import (
    DependencyResult,
    SeedResult,
)
from bioetl.domain.composite.state import CompositePipelineState
from bioetl.domain.exceptions import BioETLError, InvalidStateError
from bioetl.domain.ports import ExecutionMetricsRunnerPort

__all__ = ["CompositeRunnerStageMixin"]


class CompositeRunnerStageMixin(
    _CompositeRunnerStageEnrichmentMixin,
    _CompositeRunnerStageSupportMixin,
):
    """Mixin with seed/dependencies/enrichment stage orchestration."""

    async def _execute_seed_phase(
        self: _CompositeRunnerStageHostProtocol,
        state: CompositeCheckpointState,
    ) -> tuple[CompositeCheckpointState, SeedResult]:
        """Execute the seed phase or resume from checkpoint."""
        if not state.seed_completed:
            return await self._run_seed_with_fsm(state)

        state = self._resume_seed_phase(state)
        return state, SeedResult(pipeline_name=self._config.seed.pipeline, resumed=True)

    def _resume_seed_phase(
        self: _CompositeRunnerStageHostProtocol,
        state: CompositeCheckpointState,
    ) -> CompositeCheckpointState:
        """Normalize resumed seed state and emit resume logging."""
        self._logger.info(
            "Seed already completed, resuming from checkpoint",
            composite=self._config.name,
            run_id=self._run_id_str,
        )
        if state.state != CompositePipelineState.SEED_COMPLETED:
            previous_state = state.state
            state = apply_recovery_checkpoint_transition(
                state,
                CompositePipelineState.SEED_COMPLETED,
                reason="seed_resume_completed_checkpoint",
                clock=getattr(self, "_clock", None),
            )
            self._fsm.log_fsm_transition(
                from_state=previous_state,
                to_state=CompositePipelineState.SEED_COMPLETED,
                stage="seed_resume",
            )
        return state

    async def _run_seed_with_fsm(
        self: _CompositeRunnerStageHostProtocol,
        state: CompositeCheckpointState,
    ) -> tuple[CompositeCheckpointState, SeedResult]:
        """Run seed pipeline with FSM state transitions."""
        state = await self._start_seed_phase(state)

        try:
            seed_result = await self._call_run_seed()
        except (*PIPELINE_EXECUTION_ERRORS, BioETLError) as error:
            await self._handle_seed_phase_exception(state, error)
            raise

        state = await self._complete_seed_phase(state, seed_result)
        return state, seed_result

    async def _execute_dependencies_phase(
        self: _CompositeRunnerStageHostProtocol,
        state: CompositeCheckpointState,
        keys_df: pl.DataFrame,
    ) -> tuple[CompositeCheckpointState, dict[str, DependencyResult]]:
        """Execute dependencies stage and persist FSM/checkpoint transitions."""
        if not self._has_dependencies_configured():
            return await self._skip_dependencies_phase(state)

        prepared_context = self._prepare_dependencies_run_context()

        state = await self._start_dependencies_phase(
            state,
            context=prepared_context,
        )

        return await self._execute_started_dependencies_phase(
            state,
            context=prepared_context,
            keys_df=keys_df,
        )

    async def _execute_started_dependencies_phase(
        self: _CompositeRunnerStageHostProtocol,
        state: CompositeCheckpointState,
        *,
        context: _PreparedDependenciesRunContext,
        keys_df: pl.DataFrame,
    ) -> tuple[CompositeCheckpointState, dict[str, DependencyResult]]:
        """Run and postprocess dependencies after the phase has been started."""
        try:
            dependency_results = await self._run_dependencies(
                context=context,
                keys_df=keys_df,
                state=state,
            )
        except (*PIPELINE_EXECUTION_ERRORS, BioETLError) as error:
            await self._handle_dependencies_phase_exception(state, error)
            raise

        return await self._postprocess_dependency_results(state, dependency_results)

    async def _skip_dependencies_phase(
        self: _CompositeRunnerStageHostProtocol,
        state: CompositeCheckpointState,
    ) -> tuple[CompositeCheckpointState, dict[str, DependencyResult]]:
        """Keep checkpoint state unchanged when no dependencies are configured."""
        await asyncio.sleep(0)
        return state, {}

    def _prepare_dependencies_run_context(
        self: _CompositeRunnerStageHostProtocol,
    ) -> _PreparedDependenciesRunContext:
        """Resolve dependency runtime collaborators and pipeline names for execution."""
        return build_dependencies_run_context(self)

    async def _run_dependencies(
        self: _CompositeRunnerStageHostProtocol,
        *,
        context: _PreparedDependenciesRunContext,
        keys_df: pl.DataFrame,
        state: CompositeCheckpointState,
    ) -> dict[str, DependencyResult]:
        """Run configured dependencies through the coordinator."""
        return await context.coordinator.run_dependencies(
            keys=keys_df,
            dependencies=self._config.dependencies,
            completed=state.completed_dependencies,
            runner_factory=context.runner_factory,
        )

    async def _start_dependencies_phase(
        self: _CompositeRunnerStageHostProtocol,
        state: CompositeCheckpointState,
        *,
        context: _PreparedDependenciesRunContext,
    ) -> CompositeCheckpointState:
        """Transition to DEPENDENCIES_RUNNING, persist checkpoint, and emit phase log."""
        return await start_dependencies_phase(
            self,
            state,
            dependency_pipeline_names=context.dependency_pipeline_names,
        )

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
