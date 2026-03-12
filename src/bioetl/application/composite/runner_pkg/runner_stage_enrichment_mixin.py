"""Enrichment-stage helpers for composite runner stage orchestration."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from bioetl.application.composite.runner_pkg.runner_helpers import (
    add_not_run_results,
    log_enrichment_summary,
)
from bioetl.domain.composite.result import EnrichmentResult, EnrichmentStatus
from bioetl.domain.composite.state import CompositePipelineState
from bioetl.domain.events import PipelineEvent
from bioetl.domain.exceptions import InvalidStateError

if TYPE_CHECKING:
    import polars as pl

    from bioetl.application.composite.checkpoint import CompositeCheckpointState
    from bioetl.domain.composite.config import EnricherConfig


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
        ) -> list[EnricherConfig]: ...

        def _call_check_required_enrichers(
            self,
            enrichment_results: dict[str, EnrichmentResult],
        ) -> None: ...

        async def _call_save_checkpoint_safe(
            self,
            state: CompositeCheckpointState,
            operation: str,
        ) -> bool: ...

        def _transition_state_with_fsm_log(
            self,
            state: CompositeCheckpointState,
            to_state: CompositePipelineState,
            *,
            stage: str,
            validate: bool = True,
            **transition_kwargs: object,
        ) -> CompositeCheckpointState: ...

        async def _persist_failed_state(
            self,
            state: CompositeCheckpointState,
            *,
            stage: str,
            error: str,
        ) -> CompositeCheckpointState: ...

    async def _start_enrichment_stage(
        self,
        state: CompositeCheckpointState,
        enrichers_to_run: list[EnricherConfig],
    ) -> CompositeCheckpointState:
        """Transition FSM to ENRICHING, persist checkpoint, log phase start."""
        enricher_names = [enricher.pipeline for enricher in enrichers_to_run]
        state = self._transition_state_with_fsm_log(
            state,
            CompositePipelineState.ENRICHING,
            stage="enrichment_start",
            enrichers=enricher_names,
            count=len(enrichers_to_run),
        )
        await self._call_save_checkpoint_safe(state, "enrichment_running")
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
        enrichers_to_run: list[EnricherConfig],
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
        await self._call_save_checkpoint_safe(state, "enrichment_results")

        log_enrichment_summary(enrichment_results, self._config.name, self._logger)
        return state, enrichment_results

    async def _save_failed_enrichment_state(
        self,
        state: CompositeCheckpointState,
        error: InvalidStateError,
    ) -> None:
        """Transition to FAILED, persist checkpoint, log failure."""
        state = await self._persist_failed_state(
            state,
            stage="required_enricher_failed",
            error=str(error),
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

        enrichment_results = self._finalize_enrichment_results(
            state=state,
            enrichers_to_run=enrichers_to_run,
            enrichment_results=enrichment_results,
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
            state = self._transition_to_empty_enrichment_start(state)

        if state.state == CompositePipelineState.ENRICHING:
            state = await self._complete_enrichment_stage(state)
        return state

    def _transition_to_empty_enrichment_start(
        self,
        state: CompositeCheckpointState,
    ) -> CompositeCheckpointState:
        """Emit ENRICHING transition for the no-enrichers path."""
        return self._transition_state_with_fsm_log(
            state,
            CompositePipelineState.ENRICHING,
            stage="enrichment_start_empty",
            reason="no_enrichers_to_run",
        )

    def _finalize_enrichment_results(
        self,
        state: CompositeCheckpointState,
        enrichers_to_run: list[EnricherConfig],
        enrichment_results: dict[str, EnrichmentResult],
    ) -> dict[str, EnrichmentResult]:
        """Merge checkpoint results and add NOT_RUN entries when runtime policy skips optional enrichers."""
        enrichment_results = dict(enrichment_results)
        enrichment_results.update(state.enrichment_results)

        return add_not_run_results(
            enrichment_results,
            enrichers_to_run,
            self._config.enrichers,
            state.completed_enrichers,
            self._runtime.required_only,
            self._config.name,
            self._logger,
        )

    async def _complete_enrichment_stage(
        self,
        state: CompositeCheckpointState,
    ) -> CompositeCheckpointState:
        """Transition to ENRICHMENT_COMPLETED, persist checkpoint, and emit phase log."""
        state = self._transition_state_with_fsm_log(
            state,
            CompositePipelineState.ENRICHMENT_COMPLETED,
            stage="enrichment_complete",
        )
        await self._call_save_checkpoint_safe(state, "enrichment_completed")
        self._logger.info(
            PipelineEvent.phase_completed("enrichment"),
            composite=self._config.name,
            run_id=self._run_id_str,
        )
        return state


__all__ = ["_CompositeRunnerStageEnrichmentMixin"]
