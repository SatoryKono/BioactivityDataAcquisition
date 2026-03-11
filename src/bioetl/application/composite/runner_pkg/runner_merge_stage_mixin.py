"""Merge/finalization stage helpers for CompositePipelineRunner."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.application.composite.runner_pkg.runner_constants import (
    CHECKPOINT_NON_FATAL_ERRORS,
    PIPELINE_EXECUTION_ERRORS,
)
from bioetl.application.composite.runner_pkg.runner_helpers import (
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
    from bioetl.application.composite.runner_pkg.runner import CompositeRuntimeConfig
    from bioetl.domain.composite.config import CompositeConfig, DependencyConfig, EnricherConfig
    from bioetl.domain.composite.result import (
        DependencyResult,
        EnrichmentResult,
        MergeResult,
    )
    from bioetl.domain.ports import LoggerPort

__all__ = ["CompositeRunnerMergeStageMixin"]


class CompositeRunnerMergeStageMixin:
    """Mixin containing merge execution and finalization."""

    _runtime: CompositeRuntimeConfig
    _fsm: FSMStateHelperService
    _logger: LoggerPort
    _config: CompositeConfig
    _run_id_str: str
    _merger: MergeService
    _checkpoint_manager: CompositeCheckpointService

    async def _save_checkpoint_safe(
        self,
        state: CompositeCheckpointState,
        operation: str,
    ) -> bool:  # pragma: no cover - implemented by support mixin
        raise NotImplementedError

    async def _generate_dq_reports(
        self,
        merge_result: MergeResult,
    ) -> None:  # pragma: no cover - implemented by support mixin
        raise NotImplementedError

    async def _write_cv_quarantine(
        self,
        merge_result: MergeResult,
    ) -> None:  # pragma: no cover - implemented by support mixin
        raise NotImplementedError

    async def _call_save_checkpoint_safe(
        self,
        state: CompositeCheckpointState,
        operation: str,
    ) -> bool:
        """Invoke support-layer checkpoint save helper."""
        return await self._save_checkpoint_safe(state, operation)

    async def _call_generate_dq_reports(self, merge_result: MergeResult) -> None:
        """Invoke support-layer DQ report generation helper."""
        await self._generate_dq_reports(merge_result)

    async def _call_write_cv_quarantine(self, merge_result: MergeResult) -> None:
        """Invoke support-layer quarantine write helper."""
        await self._write_cv_quarantine(merge_result)

    async def _start_merge_phase(
        self,
        state: CompositeCheckpointState,
    ) -> CompositeCheckpointState:
        """Transition checkpoint/FSM to MERGING and persist checkpoint."""
        previous_state = state.state
        self._fsm.validate_fsm_transition(
            previous_state,
            CompositePipelineState.MERGING,
        )
        merging_state = state.with_state(CompositePipelineState.MERGING)
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
        await self._call_save_checkpoint_safe(merging_state, "merging")
        return merging_state

    async def _handle_merge_phase_exception(
        self,
        state: CompositeCheckpointState,
        error: Exception,
    ) -> None:
        """Log merge-phase failure and persist FAILED checkpoint."""
        log_kwargs: dict[str, object] = {
            "composite": self._config.name,
            "run_id": self._run_id_str,
            "error": str(error),
            "error_type": type(error).__name__,
        }
        if isinstance(error, BioETLError):
            log_kwargs["reason_code"] = "unexpected_bioetl_error"
        self._logger.error("Merge failed", **log_kwargs)
        self._fsm.log_fsm_transition(
            from_state=CompositePipelineState.MERGING,
            to_state=CompositePipelineState.FAILED,
            stage="merge_failed",
            error=str(error),
        )
        failed_state = state.with_state(CompositePipelineState.FAILED)
        await self._call_save_checkpoint_safe(failed_state, "merge_failed")

    def _build_merge_inputs(
        self,
        enrichment_results: dict[str, EnrichmentResult],
        dependency_results: dict[str, DependencyResult] | None,
    ) -> tuple[list[EnricherConfig], list[DependencyConfig]]:
        """Build mergeable enrichers and dependencies for the merge stage."""
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
        return mergeable_enrichers, mergeable_dependencies

    def _handle_dry_run_merge_skip(
        self,
        state: CompositeCheckpointState,
    ) -> CompositeCheckpointState:
        """Log dry-run merge skip and leave checkpoint state unchanged."""
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
        return state

    async def _delete_checkpoint_safe(self) -> None:
        """Delete checkpoint with graceful warning-only error handling."""
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
                reason_code="checkpoint_delete_failed",
            )

    async def _execute_merge_stage(
        self,
        state: CompositeCheckpointState,
        enrichment_results: dict[str, EnrichmentResult],
        dependency_results: dict[str, DependencyResult] | None = None,
    ) -> tuple[CompositeCheckpointState, MergeResult | None]:
        """Execute merge stage or skip in dry-run mode."""
        merge_result: MergeResult | None = None

        if not self._runtime.dry_run:
            state = await self._start_merge_phase(state)

            try:
                mergeable_enrichers, mergeable_dependencies = self._build_merge_inputs(
                    enrichment_results,
                    dependency_results,
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

            except (*PIPELINE_EXECUTION_ERRORS, BioETLError) as merge_error:
                await self._handle_merge_phase_exception(state, merge_error)
                raise
        else:
            state = self._handle_dry_run_merge_skip(state)

        return state, merge_result

    async def _finalize_pipeline(self, state: CompositeCheckpointState) -> None:
        """Finalize pipeline: set COMPLETED state and clean checkpoint."""
        if state.state != CompositePipelineState.COMPLETED:
            previous_state = state.state
            self._fsm.validate_fsm_transition(
                previous_state,
                CompositePipelineState.COMPLETED,
            )
            state = state.with_state(CompositePipelineState.COMPLETED)
            self._fsm.log_fsm_transition(
                from_state=previous_state,
                to_state=CompositePipelineState.COMPLETED,
                stage="pipeline_complete",
            )
        await self._call_save_checkpoint_safe(state, "completed")
        await self._delete_checkpoint_safe()
