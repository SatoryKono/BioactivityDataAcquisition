"""Internal stage protocol/context types for composite runner."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

import polars as pl

from bioetl.application.composite.checkpoint import CompositeCheckpointState
from bioetl.application.composite.dependency_coordinator import (
    DependencyCoordinatorService,
)
from bioetl.application.composite.fsm_helper import FSMStateHelperService
from bioetl.application.composite.lifecycle_observer_service import (
    CompositeLifecycleObserverService,
)
from bioetl.domain.composite import CompositeConfig
from bioetl.domain.composite.result import DependencyResult, SeedResult
from bioetl.domain.composite.state import CompositePipelineState
from bioetl.domain.ports import ClockPort, ExecutionMetricsRunnerPort, LoggerPort


class _CompositeRunnerStageHostProtocol(Protocol):
    _config: CompositeConfig
    _logger: LoggerPort
    _observer: CompositeLifecycleObserverService
    _run_id_str: str
    _clock: ClockPort | None
    _fsm: FSMStateHelperService
    _dependency_coordinator: DependencyCoordinatorService | None
    _dependencies_runner_factory: (
        Callable[[str, pl.DataFrame], ExecutionMetricsRunnerPort] | None
    )

    async def _run_seed_with_fsm(
        self,
        state: CompositeCheckpointState,
    ) -> tuple[CompositeCheckpointState, SeedResult]: ...

    def _resume_seed_phase(
        self,
        state: CompositeCheckpointState,
    ) -> CompositeCheckpointState: ...

    async def _start_seed_phase(
        self,
        state: CompositeCheckpointState,
    ) -> CompositeCheckpointState: ...

    async def _call_run_seed(self) -> SeedResult: ...

    async def _handle_seed_phase_exception(
        self,
        state: CompositeCheckpointState,
        error: Exception,
    ) -> None: ...

    async def _complete_seed_phase(
        self,
        state: CompositeCheckpointState,
        seed_result: SeedResult,
    ) -> CompositeCheckpointState: ...

    def _has_dependencies_configured(self) -> bool: ...

    async def _skip_dependencies_phase(
        self,
        state: CompositeCheckpointState,
    ) -> tuple[CompositeCheckpointState, dict[str, DependencyResult]]: ...

    def _prepare_dependencies_run_context(
        self,
    ) -> _PreparedDependenciesRunContext: ...

    async def _start_dependencies_phase(
        self,
        state: CompositeCheckpointState,
        *,
        context: _PreparedDependenciesRunContext,
    ) -> CompositeCheckpointState: ...

    async def _run_dependencies(
        self,
        *,
        context: _PreparedDependenciesRunContext,
        keys_df: pl.DataFrame,
        state: CompositeCheckpointState,
    ) -> dict[str, DependencyResult]: ...

    async def _execute_started_dependencies_phase(
        self,
        state: CompositeCheckpointState,
        *,
        context: _PreparedDependenciesRunContext,
        keys_df: pl.DataFrame,
    ) -> tuple[CompositeCheckpointState, dict[str, DependencyResult]]: ...

    async def _handle_dependencies_phase_exception(
        self,
        state: CompositeCheckpointState,
        error: Exception,
    ) -> None: ...

    async def _postprocess_dependency_results(
        self,
        state: CompositeCheckpointState,
        dependency_results: dict[str, DependencyResult],
    ) -> tuple[CompositeCheckpointState, dict[str, DependencyResult]]: ...

    def _record_dependencies_stage_started(
        self,
        dependency_pipeline_names: list[str],
    ) -> None: ...

    def _record_dependencies_stage_completed(
        self,
        dependency_results: dict[str, DependencyResult],
    ) -> None: ...

    def _build_dependency_phase_outcome(
        self,
        dependency_results: dict[str, DependencyResult],
    ) -> _DependencyPhaseOutcome: ...

    def _collect_successful_dependencies(
        self,
        state: CompositeCheckpointState,
        dependency_results: dict[str, DependencyResult],
    ) -> CompositeCheckpointState: ...

    async def _finalize_dependencies_phase(
        self,
        state: CompositeCheckpointState,
        outcome: _DependencyPhaseOutcome,
    ) -> tuple[CompositeCheckpointState, dict[str, DependencyResult]]: ...

    def _validate_dependency_preconditions(
        self,
    ) -> tuple[
        DependencyCoordinatorService,
        Callable[[str, pl.DataFrame], ExecutionMetricsRunnerPort],
    ]: ...

    def _find_required_failures(
        self,
        results: dict[str, DependencyResult],
    ) -> list[str]: ...

    async def _fail_required_dependencies(
        self,
        state: CompositeCheckpointState,
        required_failed: list[str],
    ) -> None: ...

    def _summarize_dependency_outcomes(
        self,
        dependency_results: dict[str, DependencyResult],
    ) -> tuple[int, int]: ...

    async def _complete_dependencies_phase(
        self,
        state: CompositeCheckpointState,
        *,
        succeeded: int,
        failed: int,
    ) -> CompositeCheckpointState: ...

    async def _persist_failed_state(
        self,
        state: CompositeCheckpointState,
        *,
        stage: str,
        error: str,
    ) -> CompositeCheckpointState: ...

    def _transition_state_with_fsm_log(
        self,
        state: CompositeCheckpointState,
        to_state: CompositePipelineState,
        *,
        stage: str,
        validate: bool = True,
        **transition_kwargs: object,
    ) -> CompositeCheckpointState: ...

    async def _call_save_checkpoint_safe(
        self,
        state: CompositeCheckpointState,
        operation: str,
    ) -> bool: ...


@dataclass(frozen=True, slots=True)
class _PreparedDependenciesRunContext:
    """Resolved runtime collaborators needed for the dependencies phase."""

    coordinator: DependencyCoordinatorService
    runner_factory: Callable[[str, pl.DataFrame], ExecutionMetricsRunnerPort]
    dependency_pipeline_names: list[str]


@dataclass(frozen=True, slots=True)
class _DependencyPhaseOutcome:
    """Normalized dependency-phase outcome used during finalization."""

    dependency_results: dict[str, DependencyResult]
    required_failed: list[str]
    succeeded: int
    failed: int
