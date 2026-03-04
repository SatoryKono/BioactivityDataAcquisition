"""Stage execution helpers for CompositePipelineRunner."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, cast

from bioetl.application.composite.runner_constants import (
    CHECKPOINT_NON_FATAL_ERRORS,
    PIPELINE_EXECUTION_ERRORS,
)
from bioetl.application.composite.runner_helpers import (
    add_not_run_results,
    log_enrichment_summary,
)
from bioetl.domain.composite.result import (
    DependencyResult,
    EnrichmentResult,
    EnrichmentStatus,
    SeedResult,
)
from bioetl.domain.composite.state import CompositePipelineState
from bioetl.domain.events import PipelineEvent
from bioetl.domain.exceptions import BioETLError

if TYPE_CHECKING:
    import polars as pl

    from bioetl.application.composite.checkpoint import (
        CompositeCheckpointService,
        CompositeCheckpointState,
    )
    from bioetl.application.composite.coordinator import EnrichmentCoordinatorService
    from bioetl.application.composite.dependency_coordinator import (
        DependencyCoordinatorService,
    )
    from bioetl.application.composite.fsm_helper import FSMStateHelperService
    from bioetl.application.composite.runner import CompositeRuntimeConfig
    from bioetl.application.core.runner import PipelineRunner
    from bioetl.domain.composite.config import CompositeConfig, EnricherConfig
    from bioetl.domain.ports import LoggerPort

__all__ = ["CompositeRunnerStageHelper"]


class _CompositeRunnerStageSupportMixin:
    """Shared helper calls and small guards for stage orchestration."""

    _config: CompositeConfig
    _runtime: CompositeRuntimeConfig
    _logger: LoggerPort
    _run_id_str: str
    _fsm: FSMStateHelperService
    _checkpoint_manager: CompositeCheckpointService
    _dependency_coordinator: DependencyCoordinatorService | None
    _dependencies_runner_factory: Callable[[str, pl.DataFrame], PipelineRunner] | None
    _coordinator: EnrichmentCoordinatorService
    _enricher_runner_factory: Callable[[str, pl.DataFrame], PipelineRunner]

    async def _call_save_checkpoint_safe(
        self,
        state: CompositeCheckpointState,
        operation: str,
    ) -> bool:
        """Invoke support-layer checkpoint save helper."""
        save_checkpoint = cast(
            "Callable[[CompositeCheckpointState, str], Awaitable[bool]]",
            getattr(self, "_save_checkpoint_safe"),
        )
        return await save_checkpoint(state, operation)

    async def _call_run_seed(self) -> SeedResult:
        """Invoke support-layer seed runner helper."""
        run_seed = cast(
            "Callable[[], Awaitable[SeedResult]]",
            getattr(self, "_run_seed"),
        )
        return await run_seed()

    def _call_get_enrichers_to_run(
        self,
        state: CompositeCheckpointState,
    ) -> list[EnricherConfig]:
        """Invoke support-layer enricher selection helper."""
        get_enrichers = cast(
            "Callable[[CompositeCheckpointState], list[EnricherConfig]]",
            getattr(self, "_get_enrichers_to_run"),
        )
        return get_enrichers(state)

    def _call_check_required_enrichers(
        self,
        enrichment_results: dict[str, EnrichmentResult],
    ) -> None:
        """Invoke support-layer required-enricher validation helper."""
        check_required = cast(
            "Callable[[dict[str, EnrichmentResult]], None]",
            getattr(self, "_check_required_enrichers"),
        )
        check_required(enrichment_results)

    def _has_dependencies_configured(self) -> bool:
        """Check if dependencies phase is configured and ready."""
        return bool(
            self._config.dependencies
            and self._dependency_coordinator
            and self._dependencies_runner_factory
        )

    def _find_required_failures(
        self,
        results: dict[str, DependencyResult],
    ) -> list[str]:
        """Find required dependencies that failed."""
        failed: list[str] = []
        for name, result in results.items():
            if result.is_success:
                continue
            dep_cfg = self._config.get_dependency(name)
            if dep_cfg and dep_cfg.required:
                failed.append(name)
        return failed


class CompositeRunnerStageHelper(_CompositeRunnerStageSupportMixin):
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
        previous_state = state.state
        self._fsm.validate_fsm_transition(
            previous_state,
            CompositePipelineState.SEED_RUNNING,
        )
        state = state.with_state(CompositePipelineState.SEED_RUNNING)
        self._fsm.log_fsm_transition(
            from_state=previous_state,
            to_state=CompositePipelineState.SEED_RUNNING,
            stage="seed_start",
        )
        self._logger.info(
            PipelineEvent.phase_started("seed"),
            composite=self._config.name,
            run_id=self._run_id_str,
        )
        await self._call_save_checkpoint_safe(state, "seed_running")

        try:
            seed_result = await self._call_run_seed()
        except PIPELINE_EXECUTION_ERRORS as error:
            self._logger.error(
                "Seed pipeline failed",
                composite=self._config.name,
                run_id=self._run_id_str,
                seed_pipeline=self._config.seed.pipeline,
                error=str(error),
                error_type=type(error).__name__,
            )
            self._fsm.log_fsm_transition(
                from_state=CompositePipelineState.SEED_RUNNING,
                to_state=CompositePipelineState.FAILED,
                stage="seed_failed",
                error=str(error),
            )
            failed_state = state.with_state(CompositePipelineState.FAILED)
            await self._call_save_checkpoint_safe(failed_state, "seed_failed")
            raise
        except BioETLError as error:
            self._logger.error(
                "Seed pipeline failed",
                composite=self._config.name,
                run_id=self._run_id_str,
                seed_pipeline=self._config.seed.pipeline,
                error=str(error),
                error_type=type(error).__name__,
                reason_code="unexpected_bioetl_error",
            )
            self._fsm.log_fsm_transition(
                from_state=CompositePipelineState.SEED_RUNNING,
                to_state=CompositePipelineState.FAILED,
                stage="seed_failed",
                error=str(error),
            )
            failed_state = state.with_state(CompositePipelineState.FAILED)
            await self._call_save_checkpoint_safe(failed_state, "seed_failed")
            raise

        state = state.with_seed_completed(seed_result)
        self._fsm.log_fsm_transition(
            from_state=CompositePipelineState.SEED_RUNNING,
            to_state=CompositePipelineState.SEED_COMPLETED,
            stage="seed_complete",
            records_extracted=seed_result.records_extracted,
            records_silver=seed_result.records_silver,
        )
        self._logger.info(
            PipelineEvent.phase_completed("seed"),
            composite=self._config.name,
            run_id=self._run_id_str,
            records_extracted=seed_result.records_extracted,
            records_silver=seed_result.records_silver,
        )
        await self._call_save_checkpoint_safe(state, "seed_completed")
        return state, seed_result

    async def _execute_dependencies_phase(
        self,
        state: CompositeCheckpointState,
        keys_df: pl.DataFrame,
    ) -> tuple[CompositeCheckpointState, dict[str, DependencyResult]]:
        """Execute the dependencies phase if configured."""
        dependency_results: dict[str, DependencyResult] = {}
        if not self._has_dependencies_configured():
            return state, dependency_results

        assert self._dependency_coordinator is not None
        assert self._dependencies_runner_factory is not None

        previous_state = state.state
        self._fsm.validate_fsm_transition(
            previous_state,
            CompositePipelineState.DEPENDENCIES_RUNNING,
        )
        state = state.with_state(CompositePipelineState.DEPENDENCIES_RUNNING)
        await self._checkpoint_manager.save(state)

        dep_pipelines = [
            dependency.pipeline for dependency in self._config.dependencies
        ]
        self._fsm.log_fsm_transition(
            from_state=previous_state,
            to_state=CompositePipelineState.DEPENDENCIES_RUNNING,
            stage="dependencies_start",
            dependencies=dep_pipelines,
            count=len(dep_pipelines),
        )
        self._logger.info(
            PipelineEvent.phase_started("dependencies"),
            composite=self._config.name,
            run_id=self._run_id_str,
            dependencies=dep_pipelines,
            count=len(dep_pipelines),
        )

        dependency_results = await self._dependency_coordinator.run_dependencies(
            keys=keys_df,
            dependencies=self._config.dependencies,
            completed=state.completed_dependencies,
            runner_factory=self._dependencies_runner_factory,
            dependency_configs={
                dependency.pipeline: dependency
                for dependency in self._config.dependencies
            },
        )

        for dep_name, dep_result in dependency_results.items():
            if dep_result.is_success:
                state = state.with_dependency_completed(dep_name, dep_result)

        required_failed = self._find_required_failures(dependency_results)
        if required_failed:
            state = state.with_state(CompositePipelineState.FAILED)
            await self._checkpoint_manager.save(state)
            raise RuntimeError(f"Required dependencies failed: {required_failed}")

        previous_state = state.state
        state = state.with_state(CompositePipelineState.DEPENDENCIES_COMPLETED)
        succeeded = sum(
            1 for result in dependency_results.values() if result.is_success
        )
        failed = len(dependency_results) - succeeded
        self._fsm.log_fsm_transition(
            from_state=previous_state,
            to_state=CompositePipelineState.DEPENDENCIES_COMPLETED,
            stage="dependencies_complete",
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
        await self._checkpoint_manager.save(state)
        return state, dependency_results

    async def _execute_enrichment_phase(
        self,
        state: CompositeCheckpointState,
        keys_df: pl.DataFrame,
    ) -> tuple[CompositeCheckpointState, dict[str, EnrichmentResult]]:
        """Execute the enrichment phase."""
        enrichers_to_run = self._call_get_enrichers_to_run(state)
        enrichment_results: dict[str, EnrichmentResult] = {}

        if enrichers_to_run:
            enricher_names = [enricher.pipeline for enricher in enrichers_to_run]
            previous_state = state.state
            self._fsm.validate_fsm_transition(
                previous_state,
                CompositePipelineState.ENRICHING,
            )
            state = state.with_state(CompositePipelineState.ENRICHING)
            await self._checkpoint_manager.save(state)

            self._fsm.log_fsm_transition(
                from_state=previous_state,
                to_state=CompositePipelineState.ENRICHING,
                stage="enrichment_start",
                enrichers=enricher_names,
                count=len(enrichers_to_run),
            )
            self._logger.info(
                PipelineEvent.phase_started("enrichment"),
                composite=self._config.name,
                run_id=self._run_id_str,
                enrichers=enricher_names,
                count=len(enrichers_to_run),
            )

            enrichment_results = await self._coordinator.run_enrichers(
                keys=keys_df,
                enrichers=enrichers_to_run,
                completed=state.completed_enrichers,
                runner_factory=self._enricher_runner_factory,
            )

            for name, result in enrichment_results.items():
                if result.is_success or result.status == EnrichmentStatus.SKIPPED:
                    state = state.with_enricher_completed(name, result)
            await self._checkpoint_manager.save(state)

            log_enrichment_summary(enrichment_results, self._config.name, self._logger)
        else:
            self._logger.info(
                "No enrichers to run, skipping enrichment stage",
                composite=self._config.name,
                reason="all_completed_or_filtered",
            )

        enrichment_results.update(state.enrichment_results)

        enrichment_results = add_not_run_results(
            enrichment_results,
            enrichers_to_run,
            self._config.enrichers,
            state.completed_enrichers,
            self._runtime.required_only,
            self._config.name,
            self._logger,
        )

        try:
            self._call_check_required_enrichers(enrichment_results)
        except RuntimeError as error:
            previous_state = state.state
            state = state.with_state(CompositePipelineState.FAILED)
            self._fsm.log_fsm_transition(
                from_state=previous_state,
                to_state=CompositePipelineState.FAILED,
                stage="required_enricher_failed",
                error=str(error),
            )
            try:
                await self._checkpoint_manager.save(state)
            except CHECKPOINT_NON_FATAL_ERRORS as save_error:
                self._logger.warning(
                    "Failed to save FAILED state to checkpoint",
                    composite=self._config.name,
                    run_id=self._run_id_str,
                    error=str(save_error),
                    error_type=type(save_error).__name__,
                )
            except BioETLError as save_error:
                self._logger.warning(
                    "Failed to save FAILED state to checkpoint",
                    composite=self._config.name,
                    run_id=self._run_id_str,
                    error=str(save_error),
                    error_type=type(save_error).__name__,
                    reason_code="unexpected_bioetl_error",
                )
            self._logger.error(
                "Required enricher failed, pipeline transitioning to FAILED",
                composite=self._config.name,
                run_id=self._run_id_str,
                error=str(error),
            )
            raise

        return state, enrichment_results

    async def _transition_to_enrichment_completed(
        self,
        state: CompositeCheckpointState,
    ) -> CompositeCheckpointState:
        """Transition FSM state to ENRICHMENT_COMPLETED."""
        if state.state in (
            CompositePipelineState.SEED_COMPLETED,
            CompositePipelineState.DEPENDENCIES_COMPLETED,
        ):
            previous_state = state.state
            self._fsm.validate_fsm_transition(
                previous_state,
                CompositePipelineState.ENRICHING,
            )
            state = state.with_state(CompositePipelineState.ENRICHING)
            self._fsm.log_fsm_transition(
                from_state=previous_state,
                to_state=CompositePipelineState.ENRICHING,
                stage="enrichment_start_empty",
                reason="no_enrichers_to_run",
            )

        if state.state == CompositePipelineState.ENRICHING:
            enriching_state = state.state
            self._fsm.validate_fsm_transition(
                enriching_state,
                CompositePipelineState.ENRICHMENT_COMPLETED,
            )
            state = state.with_state(CompositePipelineState.ENRICHMENT_COMPLETED)
            await self._call_save_checkpoint_safe(state, "enrichment_completed")

            self._fsm.log_fsm_transition(
                from_state=enriching_state,
                to_state=CompositePipelineState.ENRICHMENT_COMPLETED,
                stage="enrichment_complete",
            )
            self._logger.info(
                PipelineEvent.phase_completed("enrichment"),
                composite=self._config.name,
                run_id=self._run_id_str,
            )
        return state
