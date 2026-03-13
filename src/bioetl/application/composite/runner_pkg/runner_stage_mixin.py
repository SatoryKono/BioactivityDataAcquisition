"""Stage execution helpers for CompositePipelineRunner."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

import polars as pl

from bioetl.application.composite.checkpoint import CompositeCheckpointState
from bioetl.application.composite.dependency_coordinator import (
    DependencyCoordinatorService,
)
from bioetl.application.composite.fsm_helper import FSMStateHelperService
from bioetl.application.composite.runner_pkg.runner_constants import (
    PIPELINE_EXECUTION_ERRORS,
)
from bioetl.application.composite.runner_pkg.runner_stage_enrichment_mixin import (
    _CompositeRunnerStageEnrichmentMixin,
)
from bioetl.application.composite.runner_pkg.runner_stage_support_mixin import (
    _CompositeRunnerStageSupportMixin,
)
from bioetl.domain.composite.config import CompositeConfig
from bioetl.domain.composite.result import (
    DependencyResult,
    SeedResult,
)
from bioetl.domain.composite.state import CompositePipelineState
from bioetl.domain.events import PipelineEvent
from bioetl.domain.exceptions import BioETLError, InvalidStateError
from bioetl.domain.ports import ExecutionMetricsRunnerPort, LoggerPort


class _CompositeRunnerStageHostProtocol(Protocol):
    _config: CompositeConfig
    _logger: LoggerPort
    _run_id_str: str
    _fsm: FSMStateHelperService
    _dependency_coordinator: DependencyCoordinatorService | None
    _dependencies_runner_factory: (
        Callable[[str, pl.DataFrame], ExecutionMetricsRunnerPort] | None
    )

    async def _run_seed_with_fsm(
        self,
        state: CompositeCheckpointState,
    ) -> tuple[CompositeCheckpointState, SeedResult]: ...

    def _resume_seed_phase(
        self,
        state: CompositeCheckpointState,
    ) -> CompositeCheckpointState: ...

    async def _start_seed_phase(
        self,
        state: CompositeCheckpointState,
    ) -> CompositeCheckpointState: ...

    async def _call_run_seed(self) -> SeedResult: ...

    async def _handle_seed_phase_exception(
        self,
        state: CompositeCheckpointState,
        error: Exception,
    ) -> None: ...

    async def _complete_seed_phase(
        self,
        state: CompositeCheckpointState,
        seed_result: SeedResult,
    ) -> CompositeCheckpointState: ...

    def _has_dependencies_configured(self) -> bool: ...

    async def _skip_dependencies_phase(
        self,
        state: CompositeCheckpointState,
    ) -> tuple[CompositeCheckpointState, dict[str, DependencyResult]]: ...

    def _prepare_dependencies_run_context(
        self,
    ) -> _PreparedDependenciesRunContext: ...

    async def _start_dependencies_phase(
        self,
        state: CompositeCheckpointState,
        *,
        context: _PreparedDependenciesRunContext,
    ) -> CompositeCheckpointState: ...

    async def _run_dependencies(
        self,
        *,
        context: _PreparedDependenciesRunContext,
        keys_df: pl.DataFrame,
        state: CompositeCheckpointState,
    ) -> dict[str, DependencyResult]: ...

    async def _handle_dependencies_phase_exception(
        self,
        state: CompositeCheckpointState,
        error: Exception,
    ) -> None: ...

    async def _postprocess_dependency_results(
        self,
        state: CompositeCheckpointState,
        dependency_results: dict[str, DependencyResult],
    ) -> tuple[CompositeCheckpointState, dict[str, DependencyResult]]: ...

    def _build_dependency_phase_outcome(
        self,
        dependency_results: dict[str, DependencyResult],
    ) -> _DependencyPhaseOutcome: ...

    def _collect_successful_dependencies(
        self,
        state: CompositeCheckpointState,
        dependency_results: dict[str, DependencyResult],
    ) -> CompositeCheckpointState: ...

    async def _finalize_dependencies_phase(
        self,
        state: CompositeCheckpointState,
        outcome: _DependencyPhaseOutcome,
    ) -> tuple[CompositeCheckpointState, dict[str, DependencyResult]]: ...

    def _validate_dependency_preconditions(
        self,
    ) -> tuple[
        DependencyCoordinatorService,
        Callable[[str, pl.DataFrame], ExecutionMetricsRunnerPort],
    ]: ...

    def _find_required_failures(
        self,
        results: dict[str, DependencyResult],
    ) -> list[str]: ...

    async def _fail_required_dependencies(
        self,
        state: CompositeCheckpointState,
        required_failed: list[str],
    ) -> None: ...

    def _summarize_dependency_outcomes(
        self,
        dependency_results: dict[str, DependencyResult],
    ) -> tuple[int, int]: ...

    async def _complete_dependencies_phase(
        self,
        state: CompositeCheckpointState,
        *,
        succeeded: int,
        failed: int,
    ) -> CompositeCheckpointState: ...

    async def _persist_failed_state(
        self,
        state: CompositeCheckpointState,
        *,
        stage: str,
        error: str,
    ) -> CompositeCheckpointState: ...

    def _transition_state_with_fsm_log(
        self,
        state: CompositeCheckpointState,
        to_state: CompositePipelineState,
        *,
        stage: str,
        validate: bool = True,
        **transition_kwargs: object,
    ) -> CompositeCheckpointState: ...

    async def _call_save_checkpoint_safe(
        self,
        state: CompositeCheckpointState,
        operation: str,
    ) -> bool: ...


@dataclass(frozen=True, slots=True)
class _PreparedDependenciesRunContext:
    """Resolved runtime collaborators needed for the dependencies phase."""

    coordinator: DependencyCoordinatorService
    runner_factory: Callable[[str, pl.DataFrame], ExecutionMetricsRunnerPort]
    dependency_pipeline_names: list[str]


@dataclass(frozen=True, slots=True)
class _DependencyPhaseOutcome:
    """Normalized dependency-phase outcome used during finalization."""

    dependency_results: dict[str, DependencyResult]
    required_failed: list[str]
    succeeded: int
    failed: int


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
            state = state.with_state(CompositePipelineState.SEED_COMPLETED)
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

        try:
            dependency_results = await self._run_dependencies(
                context=prepared_context,
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
        return state, {}

    def _prepare_dependencies_run_context(
        self: _CompositeRunnerStageHostProtocol,
    ) -> _PreparedDependenciesRunContext:
        """Resolve dependency runtime collaborators and pipeline names for execution."""
        coordinator, runner_factory = self._validate_dependency_preconditions()
        dependency_pipeline_names = [
            dependency.pipeline for dependency in self._config.dependencies
        ]
        return _PreparedDependenciesRunContext(
            coordinator=coordinator,
            runner_factory=runner_factory,
            dependency_pipeline_names=dependency_pipeline_names,
        )

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
        dependencies = context.dependency_pipeline_names
        state = self._transition_state_with_fsm_log(
            state,
            CompositePipelineState.DEPENDENCIES_RUNNING,
            stage="dependencies_start",
            dependencies=dependencies,
            count=len(dependencies),
        )
        await self._call_save_checkpoint_safe(state, "dependencies_running")
        self._logger.info(
            PipelineEvent.phase_started("dependencies"),
            composite=self._config.name,
            run_id=self._run_id_str,
            dependencies=dependencies,
            count=len(dependencies),
        )
        return state

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
        required_failed = self._find_required_failures(dependency_results)
        succeeded, failed = self._summarize_dependency_outcomes(dependency_results)
        return _DependencyPhaseOutcome(
            dependency_results=dependency_results,
            required_failed=required_failed,
            succeeded=succeeded,
            failed=failed,
        )

    def _validate_dependency_preconditions(
        self: _CompositeRunnerStageHostProtocol,
    ) -> tuple[
        DependencyCoordinatorService,
        Callable[[str, pl.DataFrame], ExecutionMetricsRunnerPort],
    ]:
        """Validate that coordinator and runner factory are available.

        Returns:
            Tuple of (coordinator, runner_factory) guaranteed to be non-None.

        Raises:
            InvalidStateError: If coordinator or runner factory is None.
        """
        coordinator = self._dependency_coordinator
        runner_factory = self._dependencies_runner_factory
        if coordinator is None or runner_factory is None:
            raise InvalidStateError(
                "Dependency coordinator and runner factory must be set "
                "when dependencies are configured"
            )
        return coordinator, runner_factory

    def _collect_successful_dependencies(
        self: _CompositeRunnerStageHostProtocol,
        state: CompositeCheckpointState,
        dependency_results: dict[str, DependencyResult],
    ) -> CompositeCheckpointState:
        """Mark each successful dependency as completed on checkpoint state.

        Args:
            state: Current immutable checkpoint state.
            dependency_results: Mapping of pipeline name to DependencyResult.

        Returns:
            Updated checkpoint state with successful dependencies recorded.
        """
        for dep_name, dep_result in dependency_results.items():
            if dep_result.is_success:
                state = state.with_dependency_completed(dep_name, dep_result)
        return state

    async def _finalize_dependencies_phase(
        self: _CompositeRunnerStageHostProtocol,
        state: CompositeCheckpointState,
        outcome: _DependencyPhaseOutcome,
    ) -> tuple[CompositeCheckpointState, dict[str, DependencyResult]]:
        """Check for required failures and complete the dependencies phase.

        Validates that no required dependencies failed, transitions FSM to
        DEPENDENCIES_COMPLETED, logs summary, and persists checkpoint.

        Args:
            state: Current checkpoint state (with successful deps recorded).
            outcome: Normalized dependency-phase outcome.

        Returns:
            Updated checkpoint state and the dependency results mapping.

        Raises:
            InvalidStateError: If one or more required dependencies failed.
        """
        if outcome.required_failed:
            await self._fail_required_dependencies(state, outcome.required_failed)

        completed_state = await self._complete_dependencies_phase(
            state,
            succeeded=outcome.succeeded,
            failed=outcome.failed,
        )
        return completed_state, outcome.dependency_results

    async def _complete_dependencies_phase(
        self: _CompositeRunnerStageHostProtocol,
        state: CompositeCheckpointState,
        *,
        succeeded: int,
        failed: int,
    ) -> CompositeCheckpointState:
        """Transition to DEPENDENCIES_COMPLETED, log, and persist checkpoint."""
        completed_state = self._transition_state_with_fsm_log(
            state,
            CompositePipelineState.DEPENDENCIES_COMPLETED,
            stage="dependencies_complete",
            validate=False,
            succeeded=succeeded,
            failed=failed,
        )
        self._logger.info(
            PipelineEvent.phase_completed("dependencies"),
            composite=self._config.name,
            run_id=self._run_id_str,
            succeeded=succeeded,
            failed=failed,
        )
        await self._call_save_checkpoint_safe(completed_state, "dependencies_completed")
        return completed_state

    async def _handle_dependencies_phase_exception(
        self: _CompositeRunnerStageHostProtocol,
        state: CompositeCheckpointState,
        error: Exception,
    ) -> None:
        """Log dependency-phase failure and persist FAILED checkpoint."""
        reason_code = (
            "unexpected_bioetl_error" if isinstance(error, BioETLError) else None
        )
        log_kwargs: dict[str, object] = {
            "composite": self._config.name,
            "run_id": self._run_id_str,
            "error": str(error),
            "error_type": type(error).__name__,
        }
        if reason_code:
            log_kwargs["reason_code"] = reason_code
        self._logger.error("Dependencies phase failed", **log_kwargs)
        await self._persist_failed_state(
            state,
            stage="dependencies_failed",
            error=str(error),
        )
