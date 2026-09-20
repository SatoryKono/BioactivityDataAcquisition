"""Seed and dependency execution helpers for CompositePipelineRunner."""

from __future__ import annotations

import asyncio

import polars as pl

from bioetl.application.composite.checkpoint import (
    CompositeCheckpointState,
)
from bioetl.application.composite.runner_pkg.runner_constants import (
    PIPELINE_EXECUTION_ERRORS,
)
from bioetl.application.composite.runner_pkg.runner_stage_dependency_flow import (
    build_dependencies_run_context,
)
from bioetl.application.composite.runner_pkg.runner_stage_dependency_state_flow import (
    start_dependencies_phase,
)
from bioetl.application.composite.runner_pkg.runner_stage_seed_flow import (
    execute_seed_phase,
    resume_seed_phase,
    run_seed_with_fsm,
)
from bioetl.application.composite.runner_pkg.runner_stage_types import (
    _CompositeRunnerStageHostProtocol,
    _PreparedDependenciesRunContext,
)
from bioetl.domain.composite.result import (
    DependencyResult,
    SeedResult,
)
from bioetl.domain.exceptions import BioETLError

__all__ = ["_CompositeRunnerStageExecutionMixin"]


class _CompositeRunnerStageExecutionMixin:
    """Seed phase and dependency execution for stage orchestration."""

    async def _execute_seed_phase(
        self: _CompositeRunnerStageHostProtocol,
        state: CompositeCheckpointState,
    ) -> tuple[CompositeCheckpointState, SeedResult]:
        """Execute the seed phase or resume from checkpoint."""
        return await execute_seed_phase(self, state)

    def _resume_seed_phase(
        self: _CompositeRunnerStageHostProtocol,
        state: CompositeCheckpointState,
    ) -> CompositeCheckpointState:
        """Normalize resumed seed state and emit resume logging."""
        return resume_seed_phase(self, state)

    async def _run_seed_with_fsm(
        self: _CompositeRunnerStageHostProtocol,
        state: CompositeCheckpointState,
    ) -> tuple[CompositeCheckpointState, SeedResult]:
        """Run seed pipeline with FSM state transitions."""
        return await run_seed_with_fsm(self, state)

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
