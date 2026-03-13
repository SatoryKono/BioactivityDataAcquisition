"""Merge/finalization stage helpers for CompositePipelineRunner."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

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
    from bioetl.domain.composite.config import (
        CompositeConfig,
        DependencyConfig,
        EnricherConfig,
    )
    from bioetl.domain.composite.result import (
        DependencyResult,
        EnrichmentResult,
        MergeResult,
    )
    from bioetl.domain.ports import LoggerPort

    class _CompositeRunnerMergeStageHostProtocol(Protocol):
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
        ) -> bool: ...

        async def _generate_dq_reports(
            self,
            merge_result: MergeResult,
        ) -> None: ...

        async def _write_cv_quarantine(
            self,
            merge_result: MergeResult,
        ) -> None: ...

        async def _call_save_checkpoint_safe(
            self,
            state: CompositeCheckpointState,
            operation: str,
        ) -> bool: ...

        async def _call_generate_dq_reports(self, merge_result: MergeResult) -> None: ...

        async def _call_write_cv_quarantine(self, merge_result: MergeResult) -> None: ...

        def _transition_to_merging_state(
            self,
            state: CompositeCheckpointState,
        ) -> CompositeCheckpointState: ...

        async def _start_merge_phase(
            self,
            state: CompositeCheckpointState,
        ) -> CompositeCheckpointState: ...

        async def _handle_merge_phase_exception(
            self,
            state: CompositeCheckpointState,
            error: Exception,
        ) -> None: ...

        def _build_merge_inputs(
            self,
            enrichment_results: dict[str, EnrichmentResult],
            dependency_results: dict[str, DependencyResult] | None,
        ) -> _PreparedMergeInputs: ...

        def _prepare_merge_request(
            self,
            enrichment_results: dict[str, EnrichmentResult],
            dependency_results: dict[str, DependencyResult] | None,
        ) -> _PreparedMergeRequest: ...

        async def _run_prepared_merge_request(
            self,
            request: _PreparedMergeRequest,
        ) -> MergeResult: ...

        def _handle_dry_run_merge_skip(
            self,
            state: CompositeCheckpointState,
        ) -> CompositeCheckpointState: ...

        async def _delete_checkpoint_safe(self) -> None: ...

        def _transition_to_completed_state(
            self,
            state: CompositeCheckpointState,
        ) -> CompositeCheckpointState: ...

        async def _persist_completed_state(
            self,
            state: CompositeCheckpointState,
        ) -> None: ...

        async def _handle_merge_success(
            self,
            merge_result: MergeResult,
        ) -> None: ...

__all__ = ["CompositeRunnerMergeStageMixin"]


@dataclass(frozen=True, slots=True)
class _PreparedMergeInputs:
    """Mergeable enricher/dependency inputs resolved for the merge stage."""

    enrichers: list[EnricherConfig]
    dependencies: list[DependencyConfig]


@dataclass(frozen=True, slots=True)
class _PreparedMergeRequest:
    """Normalized merge request passed into the merger runtime seam."""

    seed_table: str
    seed_pipeline: str
    enrichers: list[EnricherConfig]
    enrichment_results: dict[str, EnrichmentResult]
    run_id: str
    dependencies: list[DependencyConfig]
    dependency_results: dict[str, DependencyResult] | None


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
        self: _CompositeRunnerMergeStageHostProtocol,
        state: CompositeCheckpointState,
        operation: str,
    ) -> bool:  # pragma: no cover - implemented by support mixin
        raise NotImplementedError

    async def _generate_dq_reports(
        self: _CompositeRunnerMergeStageHostProtocol,
        merge_result: MergeResult,
    ) -> None:  # pragma: no cover - implemented by support mixin
        raise NotImplementedError

    async def _write_cv_quarantine(
        self: _CompositeRunnerMergeStageHostProtocol,
        merge_result: MergeResult,
    ) -> None:  # pragma: no cover - implemented by support mixin
        raise NotImplementedError

    async def _call_save_checkpoint_safe(
        self: _CompositeRunnerMergeStageHostProtocol,
        state: CompositeCheckpointState,
        operation: str,
    ) -> bool:
        """Invoke support-layer checkpoint save helper."""
        return await self._save_checkpoint_safe(state, operation)

    async def _call_generate_dq_reports(
        self: _CompositeRunnerMergeStageHostProtocol,
        merge_result: MergeResult,
    ) -> None:
        """Invoke support-layer DQ report generation helper."""
        await self._generate_dq_reports(merge_result)

    async def _call_write_cv_quarantine(
        self: _CompositeRunnerMergeStageHostProtocol,
        merge_result: MergeResult,
    ) -> None:
        """Invoke support-layer quarantine write helper."""
        await self._write_cv_quarantine(merge_result)

    def _transition_to_merging_state(
        self: _CompositeRunnerMergeStageHostProtocol,
        state: CompositeCheckpointState,
    ) -> CompositeCheckpointState:
        """Return MERGING state and emit the corresponding FSM transition log."""
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
        return merging_state

    async def _start_merge_phase(
        self: _CompositeRunnerMergeStageHostProtocol,
        state: CompositeCheckpointState,
    ) -> CompositeCheckpointState:
        """Transition checkpoint/FSM to MERGING and persist checkpoint."""
        merging_state = self._transition_to_merging_state(state)
        self._logger.info(
            PipelineEvent.phase_started("merge"),
            composite=self._config.name,
            run_id=self._run_id_str,
        )
        await self._call_save_checkpoint_safe(merging_state, "merging")
        return merging_state

    async def _handle_merge_phase_exception(
        self: _CompositeRunnerMergeStageHostProtocol,
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
        self: _CompositeRunnerMergeStageHostProtocol,
        enrichment_results: dict[str, EnrichmentResult],
        dependency_results: dict[str, DependencyResult] | None,
    ) -> _PreparedMergeInputs:
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
        return _PreparedMergeInputs(
            enrichers=mergeable_enrichers,
            dependencies=mergeable_dependencies,
        )

    def _prepare_merge_request(
        self: _CompositeRunnerMergeStageHostProtocol,
        enrichment_results: dict[str, EnrichmentResult],
        dependency_results: dict[str, DependencyResult] | None,
    ) -> _PreparedMergeRequest:
        """Build the canonical merge request for the merger seam."""
        prepared_inputs = self._build_merge_inputs(
            enrichment_results,
            dependency_results,
        )
        return _PreparedMergeRequest(
            seed_table=self._config.seed.silver_table,
            seed_pipeline=self._config.seed.pipeline,
            enrichers=prepared_inputs.enrichers,
            enrichment_results=enrichment_results,
            run_id=self._run_id_str,
            dependencies=prepared_inputs.dependencies,
            dependency_results=dependency_results,
        )

    async def _run_prepared_merge_request(
        self: _CompositeRunnerMergeStageHostProtocol,
        request: _PreparedMergeRequest,
    ) -> MergeResult:
        """Run merger through a normalized request context."""
        return await self._merger.merge(
            seed_table=request.seed_table,
            enrichers=request.enrichers,
            enrichment_results=request.enrichment_results,
            run_id=request.run_id,
            seed_pipeline=request.seed_pipeline,
            dependencies=request.dependencies,
            dependency_results=request.dependency_results,
        )

    def _handle_dry_run_merge_skip(
        self: _CompositeRunnerMergeStageHostProtocol,
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

    async def _delete_checkpoint_safe(
        self: _CompositeRunnerMergeStageHostProtocol,
    ) -> None:
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

    def _transition_to_completed_state(
        self: _CompositeRunnerMergeStageHostProtocol,
        state: CompositeCheckpointState,
    ) -> CompositeCheckpointState:
        """Return finalized COMPLETED state, logging FSM transition only when needed."""
        if state.state == CompositePipelineState.COMPLETED:
            return state

        previous_state = state.state
        self._fsm.validate_fsm_transition(
            previous_state,
            CompositePipelineState.COMPLETED,
        )
        completed_state = state.with_state(CompositePipelineState.COMPLETED)
        self._fsm.log_fsm_transition(
            from_state=previous_state,
            to_state=CompositePipelineState.COMPLETED,
            stage="pipeline_complete",
        )
        return completed_state

    async def _persist_completed_state(
        self: _CompositeRunnerMergeStageHostProtocol,
        state: CompositeCheckpointState,
    ) -> None:
        """Persist finalized checkpoint state via the shared completed-operation seam."""
        await self._call_save_checkpoint_safe(state, "completed")

    async def _handle_merge_success(
        self: _CompositeRunnerMergeStageHostProtocol,
        merge_result: MergeResult,
    ) -> None:
        """Emit merge success observability and post-merge side effects."""
        self._logger.info(
            PipelineEvent.phase_completed("merge"),
            composite=self._config.name,
            run_id=self._run_id_str,
            records_merged=merge_result.records_merged,
        )
        await self._call_generate_dq_reports(merge_result)
        await self._call_write_cv_quarantine(merge_result)

    async def _execute_merge_stage(
        self: _CompositeRunnerMergeStageHostProtocol,
        state: CompositeCheckpointState,
        enrichment_results: dict[str, EnrichmentResult],
        dependency_results: dict[str, DependencyResult] | None = None,
    ) -> tuple[CompositeCheckpointState, MergeResult | None]:
        """Execute merge stage or skip in dry-run mode."""
        merge_result: MergeResult | None = None

        if not self._runtime.dry_run:
            state = await self._start_merge_phase(state)

            try:
                prepared_request = self._prepare_merge_request(
                    enrichment_results,
                    dependency_results,
                )

                merge_result = await self._run_prepared_merge_request(
                    prepared_request,
                )
                await self._handle_merge_success(merge_result)

            except (*PIPELINE_EXECUTION_ERRORS, BioETLError) as merge_error:
                await self._handle_merge_phase_exception(state, merge_error)
                raise
        else:
            state = self._handle_dry_run_merge_skip(state)

        return state, merge_result

    async def _finalize_pipeline(
        self: _CompositeRunnerMergeStageHostProtocol,
        state: CompositeCheckpointState,
    ) -> None:
        """Finalize pipeline: set COMPLETED state and clean checkpoint."""
        state = self._transition_to_completed_state(state)
        await self._persist_completed_state(state)
        await self._delete_checkpoint_safe()
