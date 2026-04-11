"""Merge/finalization stage helpers for CompositePipelineRunner."""

from __future__ import annotations

from bioetl.application.composite.checkpoint import (
    CompositeCheckpointService,
    CompositeCheckpointState,
)
from bioetl.application.composite.fsm_helper import FSMStateHelperService
from bioetl.application.composite.merger import MergeService
from bioetl.application.composite.merger_orchestration import (
    MergeExecutionRequest,
)
from bioetl.application.composite.runner_pkg.runner_completion_helpers import (
    CompositePipelineFinalizationRequest,
    finalize_pipeline,
)
from bioetl.application.composite.runner_pkg.runner_merge_stage_flow import (
    build_merge_inputs,
    build_merge_request,
    execute_merge_stage,
    execute_started_merge_phase,
    run_prepared_merge_request,
)
from bioetl.application.composite.runner_pkg.runner_merge_stage_runtime import (
    delete_checkpoint_safe,
    handle_dry_run_merge_skip,
    handle_merge_phase_exception,
    handle_merge_success,
    persist_completed_state,
    start_merge_phase,
    transition_to_completed_state,
    transition_to_merging_state,
)
from bioetl.application.composite.runner_pkg.runner_merge_stage_types import (
    _CompositeRunnerMergeStageHostProtocol,
    _PreparedMergeInputs,
)
from bioetl.application.composite.runner_pkg.runner_models import CompositeRuntimeConfig
from bioetl.domain.composite.config import CompositeConfig
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
        return await self._save_checkpoint_safe(state, operation)

    async def _call_generate_dq_reports(
        self: _CompositeRunnerMergeStageHostProtocol,
        merge_result: MergeResult,
    ) -> None:
        await self._generate_dq_reports(merge_result)

    async def _call_write_cv_quarantine(
        self: _CompositeRunnerMergeStageHostProtocol,
        merge_result: MergeResult,
    ) -> None:
        await self._write_cv_quarantine(merge_result)

    def _record_merge_stage_started(
        self: _CompositeRunnerMergeStageHostProtocol,
    ) -> None:
        """Default no-op seam for hosts without merge-stage ledger wiring."""

    def _record_merge_stage_completed(
        self: _CompositeRunnerMergeStageHostProtocol,
        merge_result: MergeResult,
    ) -> None:
        """Default no-op seam for tests or hosts without merge-stage ledger wiring."""
        del merge_result

    def _transition_to_merging_state(
        self: _CompositeRunnerMergeStageHostProtocol,
        state: CompositeCheckpointState,
    ) -> CompositeCheckpointState:
        """Return MERGING state and emit the corresponding FSM transition log."""
        return transition_to_merging_state(self, state)

    async def _start_merge_phase(
        self: _CompositeRunnerMergeStageHostProtocol,
        state: CompositeCheckpointState,
    ) -> CompositeCheckpointState:
        """Transition checkpoint/FSM to MERGING and persist checkpoint."""
        return await start_merge_phase(self, state)

    async def _handle_merge_phase_exception(
        self: _CompositeRunnerMergeStageHostProtocol,
        state: CompositeCheckpointState,
        error: Exception,
    ) -> None:
        """Log merge-phase failure and persist FAILED checkpoint."""
        await handle_merge_phase_exception(self, state, error)

    def _build_merge_inputs(
        self: _CompositeRunnerMergeStageHostProtocol,
        enrichment_results: dict[str, EnrichmentResult],
        dependency_results: dict[str, DependencyResult] | None,
    ) -> _PreparedMergeInputs:
        """Build mergeable enrichers and dependencies for the merge stage."""
        return build_merge_inputs(self, enrichment_results, dependency_results)

    def _prepare_merge_request(
        self: _CompositeRunnerMergeStageHostProtocol,
        enrichment_results: dict[str, EnrichmentResult],
        dependency_results: dict[str, DependencyResult] | None,
    ) -> MergeExecutionRequest:
        """Build the canonical merge request for the merger seam."""
        return build_merge_request(self, enrichment_results, dependency_results)

    async def _run_prepared_merge_request(
        self: _CompositeRunnerMergeStageHostProtocol,
        request: MergeExecutionRequest,
    ) -> MergeResult:
        """Run merger through a normalized request context."""
        return await run_prepared_merge_request(self, request)

    async def _execute_started_merge_phase(
        self: _CompositeRunnerMergeStageHostProtocol,
        state: CompositeCheckpointState,
        *,
        enrichment_results: dict[str, EnrichmentResult],
        dependency_results: dict[str, DependencyResult] | None,
    ) -> MergeResult:
        """Run merge after the phase has been started and handle success/errors."""
        return await execute_started_merge_phase(
            self,
            state,
            enrichment_results=enrichment_results,
            dependency_results=dependency_results,
        )

    def _handle_dry_run_merge_skip(
        self: _CompositeRunnerMergeStageHostProtocol,
        state: CompositeCheckpointState,
    ) -> CompositeCheckpointState:
        """Log dry-run merge skip and leave checkpoint state unchanged."""
        return handle_dry_run_merge_skip(self, state)

    async def _delete_checkpoint_safe(
        self: _CompositeRunnerMergeStageHostProtocol,
    ) -> None:
        """Delete checkpoint with graceful warning-only error handling."""
        await delete_checkpoint_safe(self)

    def _transition_to_completed_state(
        self: _CompositeRunnerMergeStageHostProtocol,
        state: CompositeCheckpointState,
    ) -> CompositeCheckpointState:
        """Return finalized COMPLETED state, logging FSM transition only when needed."""
        return transition_to_completed_state(self, state)

    async def _persist_completed_state(
        self: _CompositeRunnerMergeStageHostProtocol,
        state: CompositeCheckpointState,
    ) -> None:
        """Persist finalized checkpoint state via the shared completed-operation seam."""
        await persist_completed_state(self, state)

    async def _handle_merge_success(
        self: _CompositeRunnerMergeStageHostProtocol,
        merge_result: MergeResult,
    ) -> None:
        """Emit merge success observability and post-merge side effects."""
        await handle_merge_success(self, merge_result)

    async def _execute_merge_stage(
        self: _CompositeRunnerMergeStageHostProtocol,
        state: CompositeCheckpointState,
        enrichment_results: dict[str, EnrichmentResult],
        dependency_results: dict[str, DependencyResult] | None = None,
    ) -> tuple[CompositeCheckpointState, MergeResult | None]:
        """Execute merge stage or skip in dry-run mode."""
        return await execute_merge_stage(
            self,
            state,
            enrichment_results,
            dependency_results,
        )

    async def _finalize_pipeline(
        self: _CompositeRunnerMergeStageHostProtocol,
        state: CompositeCheckpointState,
    ) -> None:
        """Finalize pipeline: set COMPLETED state, clean checkpoint, purge orphans."""
        await finalize_pipeline(
            self,
            CompositePipelineFinalizationRequest(state=state),
        )
