"""Enrichment-phase completion helpers for composite runner stages."""

from __future__ import annotations

from bioetl.application.composite.checkpoint import CompositeCheckpointState
from bioetl.application.composite.runner_pkg.runner_helpers import (
    add_not_run_results,
)
from bioetl.application.composite.runner_pkg.runner_stage_enrichment_types import (
    _CompositeRunnerStageEnrichmentHostProtocol,
    _PreparedEnrichmentRunContext,
)
from bioetl.application.runtime_clock import resolve_runtime_clock
from bioetl.domain.composite.result import EnrichmentResult, EnrichmentStatus
from bioetl.domain.composite.state import CompositePipelineState
from bioetl.domain.exceptions import InvalidStateError

__all__ = ["_CompositeRunnerStageEnrichmentCompletionMixin"]


class _CompositeRunnerStageEnrichmentCompletionMixin:
    """Host mixin for enrichment phase completion and final transition."""

    async def _transition_to_enrichment_completed(
        self: _CompositeRunnerStageEnrichmentHostProtocol,
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
        self: _CompositeRunnerStageEnrichmentHostProtocol,
        state: CompositeCheckpointState,
    ) -> CompositeCheckpointState:
        """Emit ENRICHING transition for the no-enrichers path."""
        self._record_enrichment_stage_started([])
        return self._transition_state_with_fsm_log(
            state,
            CompositePipelineState.ENRICHING,
            stage="enrichment_start_empty",
            reason="no_enrichers_to_run",
        )

    def _finalize_enrichment_results(
        self: _CompositeRunnerStageEnrichmentHostProtocol,
        state: CompositeCheckpointState,
        context: _PreparedEnrichmentRunContext,
        enrichment_results: dict[str, EnrichmentResult],
    ) -> dict[str, EnrichmentResult]:
        """Merge checkpoint results and add NOT_RUN entries when runtime policy skips optional enrichers."""
        enrichment_results = dict(enrichment_results)
        enrichment_results.update(state.enrichment_results)

        return add_not_run_results(
            enrichment_results,
            context.enrichers_to_run,
            self._config.enrichers,
            state.completed_enrichers,
            self._runtime.required_only,
            self._config.name,
            self._logger,
        )

    def _record_completed_enrichment_results(
        self: _CompositeRunnerStageEnrichmentHostProtocol,
        state: CompositeCheckpointState,
        enrichment_results: dict[str, EnrichmentResult],
    ) -> CompositeCheckpointState:
        """Record successful or skipped enrichers in checkpoint state."""
        clock = resolve_runtime_clock(getattr(self, "_clock", None))
        for name, result in enrichment_results.items():
            if result.is_success or result.status == EnrichmentStatus.SKIPPED:
                state = state.with_enricher_completed(
                    name,
                    result,
                    clock=clock,
                )
        return state

    async def _validate_required_enrichment_results(
        self: _CompositeRunnerStageEnrichmentHostProtocol,
        state: CompositeCheckpointState,
        enrichment_results: dict[str, EnrichmentResult],
    ) -> None:
        """Validate required enrichers and persist FAILED state before re-raising."""
        try:
            self._call_check_required_enrichers(enrichment_results)
        except InvalidStateError as error:
            await self._save_failed_enrichment_state(state, error)
            raise

    async def _complete_enrichment_stage(
        self: _CompositeRunnerStageEnrichmentHostProtocol,
        state: CompositeCheckpointState,
    ) -> CompositeCheckpointState:
        """Transition to ENRICHMENT_COMPLETED, persist checkpoint, and emit phase log."""
        state = self._transition_state_with_fsm_log(
            state,
            CompositePipelineState.ENRICHMENT_COMPLETED,
            stage="enrichment_complete",
        )
        await self._call_save_checkpoint_safe(state, "enrichment_completed")
        self._observer.emit_phase_completed(
            composite_name=self._config.name,
            run_id=self._run_id_str,
            phase_name="enrichment",
        )
        return state
