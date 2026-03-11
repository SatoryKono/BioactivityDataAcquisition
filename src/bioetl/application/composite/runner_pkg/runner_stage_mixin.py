"""Stage execution helpers for CompositePipelineRunner."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.application.composite.runner_pkg.runner_constants import (
    PIPELINE_EXECUTION_ERRORS,
)
from bioetl.application.composite.runner_pkg.runner_stage_enrichment_mixin import (
    _CompositeRunnerStageEnrichmentMixin,
)
from bioetl.application.composite.runner_pkg.runner_stage_support_mixin import (
    _CompositeRunnerStageSupportMixin,
)
from bioetl.domain.composite.result import (
    DependencyResult,
    SeedResult,
)
from bioetl.domain.composite.state import CompositePipelineState
from bioetl.domain.events import PipelineEvent
from bioetl.domain.exceptions import BioETLError, InvalidStateError

if TYPE_CHECKING:
    from collections.abc import Callable

    import polars as pl

    from bioetl.application.composite.checkpoint import CompositeCheckpointState
    from bioetl.application.composite.dependency_coordinator import (
        DependencyCoordinatorService,
    )
    from bioetl.domain.ports import ExecutionMetricsRunnerPort

__all__ = ["CompositeRunnerStageMixin"]


class CompositeRunnerStageMixin(
    _CompositeRunnerStageEnrichmentMixin,
    _CompositeRunnerStageSupportMixin,
):
    """Mixin with seed/dependencies/enrichment stage orchestration."""

    async def _execute_seed_phase(
        self,
        state: CompositeCheckpointState,
    ) -> tuple[CompositeCheckpointState, SeedResult]:
        """Execute the seed phase or resume from checkpoint."""
        if not state.seed_completed:
            return await self._run_seed_with_fsm(state)

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
        return state, SeedResult(pipeline_name=self._config.seed.pipeline, resumed=True)

    async def _run_seed_with_fsm(
        self,
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
        self,
        state: CompositeCheckpointState,
        keys_df: pl.DataFrame,
    ) -> tuple[CompositeCheckpointState, dict[str, DependencyResult]]:
        """Execute dependencies stage and persist FSM/checkpoint transitions."""
        if not self._has_dependencies_configured():
            return state, {}

        coordinator, runner_factory = self._validate_dependency_preconditions()
        dependency_pipeline_names = [
            dependency.pipeline for dependency in self._config.dependencies
        ]

        state = self._transition_state_with_fsm_log(
            state,
            CompositePipelineState.DEPENDENCIES_RUNNING,
            stage="dependencies_start",
            dependencies=dependency_pipeline_names,
            count=len(dependency_pipeline_names),
        )
        await self._call_save_checkpoint_safe(state, "dependencies_running")
        self._logger.info(
            PipelineEvent.phase_started("dependencies"),
            composite=self._config.name,
            run_id=self._run_id_str,
            dependencies=dependency_pipeline_names,
            count=len(dependency_pipeline_names),
        )

        try:
            dependency_results = await coordinator.run_dependencies(
                keys=keys_df,
                dependencies=self._config.dependencies,
                completed=state.completed_dependencies,
                runner_factory=runner_factory,
            )
        except (*PIPELINE_EXECUTION_ERRORS, BioETLError) as error:
            await self._handle_dependencies_phase_exception(state, error)
            raise

        state = self._collect_successful_dependencies(state, dependency_results)
        return await self._finalize_dependencies_phase(state, dependency_results)

    def _validate_dependency_preconditions(
        self,
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
        self,
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
        self,
        state: CompositeCheckpointState,
        dependency_results: dict[str, DependencyResult],
    ) -> tuple[CompositeCheckpointState, dict[str, DependencyResult]]:
        """Check for required failures and complete the dependencies phase.

        Validates that no required dependencies failed, transitions FSM to
        DEPENDENCIES_COMPLETED, logs summary, and persists checkpoint.

        Args:
            state: Current checkpoint state (with successful deps recorded).
            dependency_results: Mapping of pipeline name to DependencyResult.

        Returns:
            Updated checkpoint state and the dependency results mapping.

        Raises:
            InvalidStateError: If one or more required dependencies failed.
        """
        required_failed = self._find_required_failures(dependency_results)
        if required_failed:
            await self._fail_required_dependencies(state, required_failed)

        succeeded, failed = self._summarize_dependency_outcomes(dependency_results)
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
        return completed_state, dependency_results

    async def _handle_dependencies_phase_exception(
        self,
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
        failed_state = self._transition_state_with_fsm_log(
            state,
            CompositePipelineState.FAILED,
            stage="dependencies_failed",
            validate=False,
            error=str(error),
        )
        await self._call_save_checkpoint_safe(failed_state, "dependencies_failed")
