"""Enrichment-stage helpers for composite runner stage orchestration."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from bioetl.application.composite.runner_constants import CHECKPOINT_NON_FATAL_ERRORS
from bioetl.application.composite.runner_helpers import (
    add_not_run_results,
    log_enrichment_summary,
)
from bioetl.domain.composite.result import EnrichmentResult, EnrichmentStatus
from bioetl.domain.composite.state import CompositePipelineState
from bioetl.domain.events import PipelineEvent
from bioetl.domain.exceptions import BioETLError, InvalidStateError

if TYPE_CHECKING:
    import polars as pl

    from bioetl.application.composite.checkpoint import CompositeCheckpointState


class _CompositeRunnerStageEnrichmentMixin:
    """Host mixin for enrichment phase execution and final transition."""

    _config: Any  # Any: concrete host provides composite runtime config object.
    _coordinator: Any  # Any: concrete host injects coordinator service.
    _enricher_runner_factory: Any  # Any: factory protocol varies by composition root.
    _checkpoint_manager: Any  # Any: checkpoint manager type varies by runtime wiring.
    _fsm: Any  # Any: FSM helper provided by host runner implementation.
    _logger: Any  # Any: logger-like object provided by host.
    _runtime: Any  # Any: runtime options container from host.
    _run_id_str: str

    if TYPE_CHECKING:

        def _call_get_enrichers_to_run(
            self,
            state: CompositeCheckpointState,
        ) -> list[Any]: ...

        def _call_check_required_enrichers(
            self,
            enrichment_results: dict[str, EnrichmentResult],
        ) -> None: ...

        async def _call_save_checkpoint_safe(
            self,
            state: CompositeCheckpointState,
            operation: str,
        ) -> bool: ...

    async def _start_enrichment_stage(
        self,
        state: CompositeCheckpointState,
        enrichers_to_run: list[Any],
    ) -> CompositeCheckpointState:
        """Transition FSM to ENRICHING, persist checkpoint, log phase start."""
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
        return state

    async def _run_enrichers_and_update_state(
        self,
        state: CompositeCheckpointState,
        keys_df: pl.DataFrame,
        enrichers_to_run: list[Any],
    ) -> tuple[CompositeCheckpointState, dict[str, EnrichmentResult]]:
        """Run enrichers, update state with results, persist checkpoint."""
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
        return state, enrichment_results

    async def _save_failed_enrichment_state(
        self,
        state: CompositeCheckpointState,
        error: InvalidStateError,
    ) -> None:
        """Transition to FAILED, persist checkpoint, log failure."""
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

    async def _execute_enrichment_phase(
        self,
        state: CompositeCheckpointState,
        keys_df: pl.DataFrame,
    ) -> tuple[CompositeCheckpointState, dict[str, EnrichmentResult]]:
        """Execute the enrichment phase."""
        enrichers_to_run = self._call_get_enrichers_to_run(state)
        enrichment_results: dict[str, EnrichmentResult] = {}

        if enrichers_to_run:
            state = await self._start_enrichment_stage(state, enrichers_to_run)
            state, enrichment_results = await self._run_enrichers_and_update_state(
                state,
                keys_df,
                enrichers_to_run,
            )
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
        except InvalidStateError as error:
            await self._save_failed_enrichment_state(state, error)
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


__all__ = ["_CompositeRunnerStageEnrichmentMixin"]
