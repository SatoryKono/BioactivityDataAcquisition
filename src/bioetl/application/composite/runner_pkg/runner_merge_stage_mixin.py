"""Merge/finalization stage helpers for CompositePipelineRunner."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from bioetl.application.composite.checkpoint import (
    CompositeCheckpointService,
    CompositeCheckpointState,
)
from bioetl.application.composite.fsm_helper import FSMStateHelperService
from bioetl.application.composite.merger_orchestration import (
    MergeExecutionRequest,
    build_merge_execution_request,
    resolve_merge_metadata_timestamp,
)
from bioetl.application.composite.runner_pkg.runner_completion_helpers import (
    CompositePipelineFinalizationRequest,
    finalize_pipeline,
)
from bioetl.application.composite.runner_pkg.runner_constants import (
    PIPELINE_EXECUTION_ERRORS,
)
from bioetl.application.composite.runner_pkg.runner_helpers import (
    get_mergeable_dependencies,
    get_mergeable_enrichers,
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
from bioetl.application.composite.runtime_models import (
    CompositeMergerPort,
    CompositeRuntimeConfig,
)
from bioetl.domain.composite import CompositeConfig
from bioetl.domain.composite.result import (
    DependencyResult,
    EnrichmentResult,
    MergeResult,
)
from bioetl.domain.exceptions import BioETLError
from bioetl.domain.ports import LoggerPort

__all__ = ["CompositeRunnerMergeStageMixin"]


def _get_explicit_merger_method(
    merger: Any,  # Any: merger may be a protocol-compatible runtime object or test double.
    method_name: str,
) -> Callable[..., Awaitable[MergeResult]] | None:
    """Ignore autovivified mock attrs; accept real or explicitly assigned methods."""
    instance_attrs = vars(merger)
    if method_name in instance_attrs:
        method = instance_attrs[method_name]
        return method if callable(method) else None
    method = getattr(type(merger), method_name, None)
    return method.__get__(merger, type(merger)) if callable(method) else None


class CompositeRunnerMergeStageMixin:
    """Mixin containing merge execution and finalization."""

    _runtime: CompositeRuntimeConfig
    _fsm: FSMStateHelperService
    _logger: LoggerPort
    _config: CompositeConfig
    _run_id_str: str
    _merger: CompositeMergerPort
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
    ) -> MergeExecutionRequest:
        """Build the canonical merge request for the merger seam."""
        prepared_inputs = self._build_merge_inputs(
            enrichment_results,
            dependency_results,
        )
        return build_merge_execution_request(
            seed_table=self._config.seed.silver_table,
            seed_pipeline=self._config.seed.pipeline,
            enrichers=prepared_inputs.enrichers,
            enrichment_results=enrichment_results,
            run_id=self._run_id_str,
            metadata_timestamp=resolve_merge_metadata_timestamp(
                getattr(self._runtime, "cached_bronze_date", None)
            ),
            dependencies=prepared_inputs.dependencies,
            dependency_results=dependency_results,
        )

    async def _run_prepared_merge_request(
        self: _CompositeRunnerMergeStageHostProtocol,
        request: MergeExecutionRequest,
    ) -> MergeResult:
        """Run merger through a normalized request context."""
        merger = self._merger
        execute_request = _get_explicit_merger_method(merger, "execute_request")
        if execute_request is not None:
            return await execute_request(request)
        merge = _get_explicit_merger_method(merger, "merge")
        if merge is None:
            raise AttributeError(
                "Merger does not implement execute_request() or merge()"
            )
        return await merge(
            request.seed_table,
            request.enrichers,
            request.enrichment_results,
            request.run_id,
            seed_pipeline=request.seed_pipeline,
            dependencies=request.dependencies,
            dependency_results=request.dependency_results,
        )

    async def _execute_started_merge_phase(
        self: _CompositeRunnerMergeStageHostProtocol,
        state: CompositeCheckpointState,
        *,
        enrichment_results: dict[str, EnrichmentResult],
        dependency_results: dict[str, DependencyResult] | None,
    ) -> MergeResult:
        """Run merge after the phase has been started and handle success/errors."""
        try:
            prepared_request = self._prepare_merge_request(
                enrichment_results,
                dependency_results,
            )
            merge_result = await self._run_prepared_merge_request(prepared_request)
            await handle_merge_success(self, merge_result)
        except (*PIPELINE_EXECUTION_ERRORS, BioETLError) as merge_error:
            await handle_merge_phase_exception(self, state, merge_error)
            raise
        return merge_result

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
        merge_result: MergeResult | None = None
        if not self._runtime.dry_run:
            state = await start_merge_phase(self, state)
            merge_result = await self._execute_started_merge_phase(
                state,
                enrichment_results=enrichment_results,
                dependency_results=dependency_results,
            )
        else:
            state = handle_dry_run_merge_skip(self, state)
        return state, merge_result

    async def _finalize_pipeline(
        self: _CompositeRunnerMergeStageHostProtocol,
        state: CompositeCheckpointState,
    ) -> None:
        """Finalize pipeline: set COMPLETED state, clean checkpoint, purge orphans."""
        await finalize_pipeline(
            self,
            CompositePipelineFinalizationRequest(state=state),
        )
