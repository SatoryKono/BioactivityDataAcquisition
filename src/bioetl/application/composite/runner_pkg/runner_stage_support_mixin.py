# Host attrs/methods are initialized by concrete classes (PD2 W1 host surface).
"""Support helpers for composite runner stage orchestration."""

from __future__ import annotations

from collections.abc import Callable

import polars as pl

from bioetl.application.composite.checkpoint import (
    CompositeCheckpointService,
    CompositeCheckpointState,
)
from bioetl.application.composite.coordinator import EnrichmentCoordinatorService
from bioetl.application.composite.dependency_coordinator import (
    DependencyCoordinatorService,
)
from bioetl.application.composite.fsm_helper import FSMStateHelperService
from bioetl.application.composite.runner_pkg.runner_stage_state_flow import (
    complete_seed_phase,
    fail_required_dependencies,
    find_required_failures,
    handle_seed_phase_exception,
    persist_failed_state,
    start_seed_phase,
    summarize_dependency_outcomes,
    transition_state_with_fsm_log,
)
from bioetl.application.composite.runner_pkg.runner_stage_support_types import (
    _CompositeRunnerStageSupportHostProtocol,
)
from bioetl.application.composite.runtime_models import CompositeRuntimeConfig
from bioetl.domain.composite import CompositeConfig, EnricherConfig
from bioetl.domain.composite.result import (
    DependencyResult,
    EnrichmentResult,
    SeedResult,
)
from bioetl.domain.composite.state import CompositePipelineState
from bioetl.domain.ports import ExecutionMetricsRunnerPort, LoggerPort


class _CompositeRunnerStageSupportMixin:
    """Shared helper calls and small guards for stage orchestration."""

    _config: CompositeConfig  # pyright: ignore[reportUninitializedInstanceVariable]
    _runtime: CompositeRuntimeConfig  # pyright: ignore[reportUninitializedInstanceVariable]
    _logger: LoggerPort  # pyright: ignore[reportUninitializedInstanceVariable]
    _run_id_str: str  # pyright: ignore[reportUninitializedInstanceVariable]
    _fsm: FSMStateHelperService  # pyright: ignore[reportUninitializedInstanceVariable]
    _checkpoint_manager: CompositeCheckpointService  # pyright: ignore[reportUninitializedInstanceVariable]
    _dependency_coordinator: DependencyCoordinatorService | None  # pyright: ignore[reportUninitializedInstanceVariable]
    _dependencies_runner_factory: (  # pyright: ignore[reportUninitializedInstanceVariable]
        Callable[[str, pl.DataFrame], ExecutionMetricsRunnerPort] | None
    )
    _coordinator: EnrichmentCoordinatorService  # pyright: ignore[reportUninitializedInstanceVariable]
    _enricher_runner_factory: Callable[[str, pl.DataFrame], ExecutionMetricsRunnerPort]  # pyright: ignore[reportUninitializedInstanceVariable]

    async def _save_checkpoint_safe(
        self: _CompositeRunnerStageSupportHostProtocol,
        state: CompositeCheckpointState,
        operation: str,
    ) -> bool:  # pragma: no cover - implemented by support mixin
        raise NotImplementedError

    async def _run_seed(
        self: _CompositeRunnerStageSupportHostProtocol,
    ) -> SeedResult:  # pragma: no cover - support mixin
        raise NotImplementedError

    def _get_enrichers_to_run(
        self: _CompositeRunnerStageSupportHostProtocol,
        state: CompositeCheckpointState,
    ) -> list[EnricherConfig]:  # pragma: no cover - implemented by support mixin
        raise NotImplementedError

    def _check_required_enrichers(
        self: _CompositeRunnerStageSupportHostProtocol,
        enrichment_results: dict[str, EnrichmentResult],
    ) -> None:  # pragma: no cover - implemented by support mixin
        raise NotImplementedError

    async def _call_save_checkpoint_safe(
        self: _CompositeRunnerStageSupportHostProtocol,
        state: CompositeCheckpointState,
        operation: str,
    ) -> bool:
        """Invoke support-layer checkpoint save helper."""
        return await self._save_checkpoint_safe(state, operation)

    async def _call_run_seed(
        self: _CompositeRunnerStageSupportHostProtocol,
    ) -> SeedResult:
        """Invoke support-layer seed runner helper."""
        return await self._run_seed()

    def _call_get_enrichers_to_run(
        self: _CompositeRunnerStageSupportHostProtocol,
        state: CompositeCheckpointState,
    ) -> list[EnricherConfig]:
        """Invoke support-layer enricher selection helper."""
        return self._get_enrichers_to_run(state)

    def _call_check_required_enrichers(
        self: _CompositeRunnerStageSupportHostProtocol,
        enrichment_results: dict[str, EnrichmentResult],
    ) -> None:
        """Invoke support-layer required-enricher validation helper."""
        self._check_required_enrichers(enrichment_results)

    def _record_seed_stage_started(
        self: _CompositeRunnerStageSupportHostProtocol,
    ) -> None:
        """Default no-op seam for hosts without control-plane ledger wiring."""

    def _record_seed_stage_completed(
        self: _CompositeRunnerStageSupportHostProtocol,
        seed_result: SeedResult,
    ) -> None:
        """Default no-op seam for hosts without control-plane ledger wiring."""
        del seed_result

    def _record_dependencies_stage_started(
        self: _CompositeRunnerStageSupportHostProtocol,
        dependency_pipeline_names: list[str],
    ) -> None:
        """Default no-op seam for hosts without control-plane ledger wiring."""
        del dependency_pipeline_names

    def _record_dependencies_stage_completed(
        self: _CompositeRunnerStageSupportHostProtocol,
        dependency_results: dict[str, DependencyResult],
    ) -> None:
        """Default no-op seam for hosts without control-plane ledger wiring."""
        del dependency_results

    def _record_enrichment_stage_started(
        self: _CompositeRunnerStageSupportHostProtocol,
        enricher_names: list[str],
    ) -> None:
        """Default no-op seam for hosts without control-plane ledger wiring."""
        del enricher_names

    def _record_enrichment_stage_completed(
        self: _CompositeRunnerStageSupportHostProtocol,
        enrichment_results: dict[str, EnrichmentResult],
    ) -> None:
        """Default no-op seam for hosts without control-plane ledger wiring."""
        del enrichment_results

    def _has_dependencies_configured(
        self: _CompositeRunnerStageSupportHostProtocol,
    ) -> bool:
        """Check if dependencies phase is configured and ready."""
        return bool(
            self._config.dependencies
            and self._dependency_coordinator
            and self._dependencies_runner_factory
        )

    def _find_required_failures(
        self: _CompositeRunnerStageSupportHostProtocol,
        results: dict[str, DependencyResult],
    ) -> list[str]:
        """Find required dependencies that failed."""
        return find_required_failures(self, results)

    def _transition_state_with_fsm_log(
        self: _CompositeRunnerStageSupportHostProtocol,
        state: CompositeCheckpointState,
        to_state: CompositePipelineState,
        *,
        stage: str,
        validate: bool = True,
        recovery_reason: str | None = None,
        **transition_kwargs: object,
    ) -> CompositeCheckpointState:
        """Transition immutable state and emit FSM log entry.

        Keeps the validate -> with_state -> log choreography in one place while
        leaving checkpoint persistence order to the caller.
        """
        return transition_state_with_fsm_log(
            self,
            state,
            to_state,
            stage=stage,
            validate=validate,
            recovery_reason=recovery_reason,
            **transition_kwargs,
        )

    async def _persist_failed_state(
        self: _CompositeRunnerStageSupportHostProtocol,
        state: CompositeCheckpointState,
        *,
        stage: str,
        error: str,
    ) -> CompositeCheckpointState:
        """Transition to FAILED and persist the checkpoint via the shared safe seam."""
        return await persist_failed_state(
            self,
            state,
            stage=stage,
            error=error,
        )

    async def _start_seed_phase(
        self: _CompositeRunnerStageSupportHostProtocol,
        state: CompositeCheckpointState,
    ) -> CompositeCheckpointState:
        """Transition checkpoint/FSM to SEED_RUNNING and persist checkpoint."""
        return await start_seed_phase(self, state)

    async def _complete_seed_phase(
        self: _CompositeRunnerStageSupportHostProtocol,
        state: CompositeCheckpointState,
        seed_result: SeedResult,
    ) -> CompositeCheckpointState:
        """Record successful seed completion and persist checkpoint."""
        return await complete_seed_phase(self, state, seed_result)

    async def _handle_seed_phase_exception(
        self: _CompositeRunnerStageSupportHostProtocol,
        state: CompositeCheckpointState,
        error: Exception,
    ) -> None:
        """Handle seed-phase failure and persist FAILED checkpoint."""
        await handle_seed_phase_exception(self, state, error)

    async def _fail_required_dependencies(
        self: _CompositeRunnerStageSupportHostProtocol,
        state: CompositeCheckpointState,
        required_failed: list[str],
    ) -> None:
        """Persist dependency failure state when required dependencies fail."""
        await fail_required_dependencies(self, state, required_failed)

    @staticmethod
    def _summarize_dependency_outcomes(
        dependency_results: dict[str, DependencyResult],
    ) -> tuple[int, int]:
        """Return counts of successful and failed dependency executions."""
        return summarize_dependency_outcomes(dependency_results)


__all__ = ["_CompositeRunnerStageSupportMixin"]
