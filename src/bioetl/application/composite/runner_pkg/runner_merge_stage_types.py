"""Internal merge-stage protocol/context types for composite runner."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from bioetl.application.composite.checkpoint import (
    CompositeCheckpointService,
    CompositeCheckpointState,
)
from bioetl.application.composite.fsm_helper import FSMStateHelperService
from bioetl.application.composite.lifecycle_observer_service import (
    CompositeLifecycleObserverService,
)
from bioetl.application.composite.merger_orchestration import (
    MergeExecutionRequest,
)
from bioetl.application.composite.runtime_models import (
    CompositeMergerProtocol,
    CompositeRuntimeConfig,
)
from bioetl.domain.composite import (
    CompositeConfig,
    DependencyConfig,
    EnricherConfig,
)
from bioetl.domain.composite.result import (
    DependencyResult,
    EnrichmentResult,
    MergeResult,
)
from bioetl.domain.ports import ClockPort, LoggerPort


class _CompositeRunnerMergeStageHostProtocol(Protocol):
    _runtime: CompositeRuntimeConfig
    _fsm: FSMStateHelperService
    _logger: LoggerPort
    _observer: CompositeLifecycleObserverService
    _config: CompositeConfig
    _run_id_str: str
    _clock: ClockPort | None
    _merger: CompositeMergerProtocol
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

    def _record_merge_stage_started(self) -> None: ...

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
    ) -> MergeExecutionRequest: ...

    async def _run_prepared_merge_request(
        self,
        request: MergeExecutionRequest,
    ) -> MergeResult: ...

    async def _execute_started_merge_phase(
        self,
        state: CompositeCheckpointState,
        *,
        enrichment_results: dict[str, EnrichmentResult],
        dependency_results: dict[str, DependencyResult] | None,
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

    def _record_merge_stage_completed(self, merge_result: MergeResult) -> None: ...


@dataclass(frozen=True, slots=True)
class _PreparedMergeInputs:
    """Mergeable enricher/dependency inputs resolved for the merge stage."""

    enrichers: list[EnricherConfig]
    dependencies: list[DependencyConfig]
