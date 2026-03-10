"""Merge/finalization stage helpers for CompositePipelineRunner."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, cast

from bioetl.application.composite.runner_constants import (
    CHECKPOINT_NON_FATAL_ERRORS,
    PIPELINE_EXECUTION_ERRORS,
)
from bioetl.application.composite.runner_helpers import (
    get_mergeable_dependencies,
    get_mergeable_enrichers,
)
from bioetl.domain.composite.state import CompositePipelineState
from bioetl.domain.events import PipelineEvent
from bioetl.domain.exceptions import BioETLError

if TYPE_CHECKING:
    from bioetl.application.composite.checkpoint import (
        CompositeCheckpointService,
        CompositeCheckpointState,
    )
    from bioetl.application.composite.fsm_helper import FSMStateHelperService
    from bioetl.application.composite.merger import MergeService
    from bioetl.application.composite.runner import CompositeRuntimeConfig
    from bioetl.domain.composite.config import CompositeConfig
    from bioetl.domain.composite.result import (
        DependencyResult,
        EnrichmentResult,
        MergeResult,
    )
    from bioetl.domain.ports import ClockPort, LoggerPort

__all__ = ["CompositeRunnerMergeStageHelper"]


class CompositeRunnerMergeStageHelper:
    """Mixin containing merge execution and finalization."""

    _runtime: CompositeRuntimeConfig
    _fsm: FSMStateHelperService
    _logger: LoggerPort
    _clock: ClockPort
    _config: CompositeConfig
    _run_id_str: str
    _merger: MergeService
    _checkpoint_manager: CompositeCheckpointService

    async def _call_save_checkpoint_safe(
        self,
        state: CompositeCheckpointState,
        operation: str,
    ) -> bool:
        """Invoke support-layer checkpoint save helper."""
        save_checkpoint = cast(
            "Callable[[CompositeCheckpointState, str], Awaitable[bool]]",
            self._save_checkpoint_safe,
        )
        return await save_checkpoint(state, operation)

    async def _call_generate_dq_reports(self, merge_result: MergeResult) -> None:
        """Invoke support-layer DQ report generation helper."""
        generate_reports = cast(
            "Callable[[MergeResult], Awaitable[None]]",
            self._generate_dq_reports,
        )
        await generate_reports(merge_result)

    async def _call_write_cv_quarantine(self, merge_result: MergeResult) -> None:
        """Invoke support-layer quarantine write helper."""
        write_quarantine = cast(
            "Callable[[MergeResult], Awaitable[None]]",
            self._write_cv_quarantine,
        )
        await write_quarantine(merge_result)

    async def _execute_merge_stage(
        self,
        state: CompositeCheckpointState,
        enrichment_results: dict[str, EnrichmentResult],
        dependency_results: dict[str, DependencyResult] | None = None,
    ) -> tuple[CompositeCheckpointState, MergeResult | None]:
        """Execute merge stage or skip in dry-run mode."""
        merge_result: MergeResult | None = None

        if not self._runtime.dry_run:
            previous_state = state.state
            self._fsm.validate_fsm_transition(
                previous_state,
                CompositePipelineState.MERGING,
            )
            state = state.with_state(
                CompositePipelineState.MERGING, updated_at=self._clock.now_utc()
            )
            await self._call_save_checkpoint_safe(state, "merging")

            self._fsm.log_fsm_transition(
                from_state=previous_state,
                to_state=CompositePipelineState.MERGING,
                stage="merge_start",
            )
            self._logger.info(
                PipelineEvent.phase_started("merge"),
                composite=self._config.name,
                run_id=self._run_id_str,
            )

            try:
                mergeable_enrichers = get_mergeable_enrichers(
                    enrichment_results,
                    self._config.enrichers,
                    self._logger,
                )
                mergeable_dependencies = get_mergeable_dependencies(
                    dependency_results or {},
                    self._config.dependencies,
                    self._logger,
                )

                merge_result = await self._merger.merge(
                    seed_table=self._config.seed.silver_table,
                    enrichers=mergeable_enrichers,
                    enrichment_results=enrichment_results,
                    run_id=self._run_id_str,
                    seed_pipeline=self._config.seed.pipeline,
                    dependencies=mergeable_dependencies,
                    dependency_results=dependency_results,
                )

                self._logger.info(
                    PipelineEvent.phase_completed("merge"),
                    composite=self._config.name,
                    run_id=self._run_id_str,
                    records_merged=merge_result.records_merged,
                )

                await self._call_generate_dq_reports(merge_result)
                await self._call_write_cv_quarantine(merge_result)

            except PIPELINE_EXECUTION_ERRORS as merge_error:
                self._fsm.log_fsm_transition(
                    from_state=CompositePipelineState.MERGING,
                    to_state=CompositePipelineState.FAILED,
                    stage="merge_failed",
                    error=str(merge_error),
                )
                self._logger.error(
                    "Merge failed",
                    composite=self._config.name,
                    run_id=self._run_id_str,
                    error=str(merge_error),
                    error_type=type(merge_error).__name__,
                )
                state = state.with_state(
                    CompositePipelineState.FAILED, updated_at=self._clock.now_utc()
                )
                await self._call_save_checkpoint_safe(state, "merge_failed")
                raise
            except BioETLError as merge_error:
                self._fsm.log_fsm_transition(
                    from_state=CompositePipelineState.MERGING,
                    to_state=CompositePipelineState.FAILED,
                    stage="merge_failed",
                    error=str(merge_error),
                )
                self._logger.error(
                    "Merge failed",
                    composite=self._config.name,
                    run_id=self._run_id_str,
                    error=str(merge_error),
                    error_type=type(merge_error).__name__,
                    reason_code="unexpected_bioetl_error",
                )
                state = state.with_state(
                    CompositePipelineState.FAILED, updated_at=self._clock.now_utc()
                )
                await self._call_save_checkpoint_safe(state, "merge_failed")
                raise
        else:
            self._fsm.log_fsm_transition(
                from_state=state.state,
                to_state=CompositePipelineState.COMPLETED,
                stage="dry_run_skip_merge",
                reason="dry_run_mode",
            )
            self._logger.info(
                "Dry run: merge skipped, pipeline completing",
                composite=self._config.name,
                run_id=self._run_id_str,
            )

        return state, merge_result

    async def _finalize_pipeline(self, state: CompositeCheckpointState) -> None:
        """Finalize pipeline: set COMPLETED state and clean checkpoint."""
        if state.state != CompositePipelineState.COMPLETED:
            previous_state = state.state
            self._fsm.validate_fsm_transition(
                previous_state,
                CompositePipelineState.COMPLETED,
            )
            state = state.with_state(
                CompositePipelineState.COMPLETED, updated_at=self._clock.now_utc()
            )
            self._fsm.log_fsm_transition(
                from_state=previous_state,
                to_state=CompositePipelineState.COMPLETED,
                stage="pipeline_complete",
            )
        await self._call_save_checkpoint_safe(state, "completed")

        try:
            await self._checkpoint_manager.delete()
        except CHECKPOINT_NON_FATAL_ERRORS as delete_error:
            self._logger.warning(
                "Failed to delete checkpoint",
                composite=self._config.name,
                run_id=self._run_id_str,
                error=str(delete_error),
                error_type=type(delete_error).__name__,
            )
        except BioETLError as delete_error:
            self._logger.warning(
                "Failed to delete checkpoint",
                composite=self._config.name,
                run_id=self._run_id_str,
                error=str(delete_error),
                error_type=type(delete_error).__name__,
                reason_code="unexpected_bioetl_error",
            )
