"""Enrichment-stage helpers for composite runner stage orchestration."""

from __future__ import annotations

import asyncio
from typing import cast

import polars as pl

from bioetl.application.composite.checkpoint import CompositeCheckpointState
from bioetl.application.composite.runner_pkg.runner_helpers import (
    add_not_run_results,
    log_enrichment_summary,
)
from bioetl.application.composite.runner_pkg.runner_stage_enrichment_types import (
    _CompositeRunnerStageEnrichmentHostProtocol,
    _PreparedEnrichmentRunContext,
)
from bioetl.application.composite.runner_pkg.runner_stage_payloads import (
    build_enrichment_stage_details,
)
from bioetl.application.composite.runner_pkg.runner_stage_start_flow import (
    start_composite_phase,
)
from bioetl.domain.composite.result import EnrichmentResult, EnrichmentStatus
from bioetl.domain.composite.state import CompositePipelineState
from bioetl.domain.exceptions import InvalidStateError


class _CompositeRunnerStageEnrichmentMixin:
    """Host mixin for enrichment phase execution and final transition."""

    def _prepare_enrichment_run_context(
        self: _CompositeRunnerStageEnrichmentHostProtocol,
        state: CompositeCheckpointState,
    ) -> _PreparedEnrichmentRunContext:
        """Resolve the enrichers selected for the current stage execution."""
        enrichers_to_run = self._call_get_enrichers_to_run(state)
        return _PreparedEnrichmentRunContext(
            enrichers_to_run=enrichers_to_run,
            enricher_names=[enricher.pipeline for enricher in enrichers_to_run],
        )

    async def _start_enrichment_stage(
        self: _CompositeRunnerStageEnrichmentHostProtocol,
        state: CompositeCheckpointState,
        context: _PreparedEnrichmentRunContext,
    ) -> CompositeCheckpointState:
        """Transition FSM to ENRICHING, persist checkpoint, log phase start."""
        stage_details = build_enrichment_stage_details(context.enricher_names)
        return await start_composite_phase(
            self,
            state,
            to_state=CompositePipelineState.ENRICHING,
            stage="enrichment_start",
            checkpoint_operation="enrichment_running",
            phase_name="enrichment",
            transition_details=stage_details,
            log_details=stage_details,
            on_started=lambda: self._record_enrichment_stage_started(
                context.enricher_names
            ),
        )

    async def _run_enrichers_and_update_state(
        self: _CompositeRunnerStageEnrichmentHostProtocol,
        state: CompositeCheckpointState,
        keys_df: pl.DataFrame,
        context: _PreparedEnrichmentRunContext,
    ) -> tuple[CompositeCheckpointState, dict[str, EnrichmentResult]]:
        """Run enrichers, update state with results, persist checkpoint."""
        enrichment_results = await self._coordinator.run_enrichers(
            keys=keys_df,
            enrichers=context.enrichers_to_run,
            completed=state.completed_enrichers,
            runner_factory=self._enricher_runner_factory,
        )

        state = self._record_completed_enrichment_results(state, enrichment_results)
        await self._call_save_checkpoint_safe(state, "enrichment_results")

        log_enrichment_summary(enrichment_results, self._config.name, self._logger)
        return state, enrichment_results

    async def _save_failed_enrichment_state(
        self: _CompositeRunnerStageEnrichmentHostProtocol,
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

    async def _skip_enrichment_stage(
        self: _CompositeRunnerStageEnrichmentHostProtocol,
        state: CompositeCheckpointState,
    ) -> tuple[CompositeCheckpointState, dict[str, EnrichmentResult]]:
        """Log skipped enrichment stage and keep checkpoint state unchanged."""
        await asyncio.sleep(0)
        self._logger.info(
            "No enrichers to run, skipping enrichment stage",
            composite=self._config.name,
            reason="all_completed_or_filtered",
        )
        return state, {}

    async def _execute_enrichment_phase(
        self: _CompositeRunnerStageEnrichmentHostProtocol,
        state: CompositeCheckpointState,
        keys_df: pl.DataFrame,
    ) -> tuple[CompositeCheckpointState, dict[str, EnrichmentResult]]:
        """Execute the enrichment phase."""
        context = self._prepare_enrichment_run_context(state)
        enrichment_results: dict[str, EnrichmentResult] = {}

        if context.enrichers_to_run:
            state = await self._start_enrichment_stage(state, context)
            state, enrichment_results = await self._run_enrichers_and_update_state(
                state,
                keys_df,
                context,
            )
        else:
            state, enrichment_results = await self._skip_enrichment_stage(
                state,
            )

        enrichment_results = self._finalize_enrichment_results(
            state=state,
            context=context,
            enrichment_results=enrichment_results,
        )

        await self._validate_required_enrichment_results(state, enrichment_results)

        return state, enrichment_results

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

        return cast(
            dict[str, EnrichmentResult],
            add_not_run_results(
                enrichment_results,
                context.enrichers_to_run,
                self._config.enrichers,
                state.completed_enrichers,
                self._runtime.required_only,
                self._config.name,
                self._logger,
            ),
        )

    def _record_completed_enrichment_results(
        self: _CompositeRunnerStageEnrichmentHostProtocol,
        state: CompositeCheckpointState,
        enrichment_results: dict[str, EnrichmentResult],
    ) -> CompositeCheckpointState:
        """Record successful or skipped enrichers in checkpoint state."""
        clock = getattr(self, "_clock", None)
        for name, result in enrichment_results.items():
            if result.is_success or result.status == EnrichmentStatus.SKIPPED:
                if clock is None:
                    state = state.with_enricher_completed(name, result)
                else:
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


__all__ = ["_CompositeRunnerStageEnrichmentMixin"]
