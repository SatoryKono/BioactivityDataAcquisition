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
from bioetl.application.composite.runner_pkg.runner_models import CompositeRuntimeConfig
from bioetl.application.composite.runner_pkg.runner_stage_support_types import (
    _CompositeRunnerStageSupportHostProtocol,
)
from bioetl.domain.composite.config import CompositeConfig, EnricherConfig
from bioetl.domain.composite.result import (
    DependencyResult,
    EnrichmentResult,
    SeedResult,
)
from bioetl.domain.composite.state import CompositePipelineState
from bioetl.domain.events import PipelineEvent
from bioetl.domain.exceptions import BioETLError, InvalidStateError
from bioetl.domain.ports import ExecutionMetricsRunnerPort, LoggerPort


class _CompositeRunnerStageSupportMixin:
    """Shared helper calls and small guards for stage orchestration."""

    _config: CompositeConfig
    _runtime: CompositeRuntimeConfig
    _logger: LoggerPort
    _run_id_str: str
    _fsm: FSMStateHelperService
    _checkpoint_manager: CompositeCheckpointService
    _dependency_coordinator: DependencyCoordinatorService | None
    _dependencies_runner_factory: (
        Callable[[str, pl.DataFrame], ExecutionMetricsRunnerPort] | None
    )
    _coordinator: EnrichmentCoordinatorService
    _enricher_runner_factory: Callable[[str, pl.DataFrame], ExecutionMetricsRunnerPort]

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

    async def _call_run_seed(self: _CompositeRunnerStageSupportHostProtocol) -> SeedResult:
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

    def _has_dependencies_configured(self: _CompositeRunnerStageSupportHostProtocol) -> bool:
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
        failed: list[str] = []
        for name, result in results.items():
            if result.is_success:
                continue
            dep_cfg = self._config.get_dependency(name)
            if dep_cfg and dep_cfg.required:
                failed.append(name)
        return failed

    def _transition_state_with_fsm_log(
        self: _CompositeRunnerStageSupportHostProtocol,
        state: CompositeCheckpointState,
        to_state: CompositePipelineState,
        *,
        stage: str,
        validate: bool = True,
        **transition_kwargs: object,
    ) -> CompositeCheckpointState:
        """Transition immutable state and emit FSM log entry.

        Keeps the validate -> with_state -> log choreography in one place while
        leaving checkpoint persistence order to the caller.
        """
        previous_state = state.state
        if validate:
            self._fsm.validate_fsm_transition(previous_state, to_state)
        next_state = state.with_state(to_state)
        self._fsm.log_fsm_transition(
            from_state=previous_state,
            to_state=to_state,
            stage=stage,
            **transition_kwargs,
        )
        return next_state

    async def _persist_failed_state(
        self: _CompositeRunnerStageSupportHostProtocol,
        state: CompositeCheckpointState,
        *,
        stage: str,
        error: str,
    ) -> CompositeCheckpointState:
        """Transition to FAILED and persist the checkpoint via the shared safe seam."""
        failed_state = self._transition_state_with_fsm_log(
            state,
            CompositePipelineState.FAILED,
            stage=stage,
            validate=False,
            error=error,
        )
        await self._call_save_checkpoint_safe(failed_state, stage)
        return failed_state

    async def _start_seed_phase(
        self: _CompositeRunnerStageSupportHostProtocol,
        state: CompositeCheckpointState,
    ) -> CompositeCheckpointState:
        """Transition checkpoint/FSM to SEED_RUNNING and persist checkpoint."""
        running_state = self._transition_state_with_fsm_log(
            state,
            CompositePipelineState.SEED_RUNNING,
            stage="seed_start",
        )
        self._logger.info(
            PipelineEvent.phase_started("seed"),
            composite=self._config.name,
            run_id=self._run_id_str,
        )
        await self._call_save_checkpoint_safe(running_state, "seed_running")
        return running_state

    async def _complete_seed_phase(
        self: _CompositeRunnerStageSupportHostProtocol,
        state: CompositeCheckpointState,
        seed_result: SeedResult,
    ) -> CompositeCheckpointState:
        """Record successful seed completion and persist checkpoint."""
        completed_state = self._transition_state_with_fsm_log(
            state.with_seed_completed(seed_result),
            CompositePipelineState.SEED_COMPLETED,
            stage="seed_complete",
            validate=False,
            records_extracted=seed_result.records_extracted,
            records_silver=seed_result.records_silver,
        )
        self._logger.info(
            PipelineEvent.phase_completed("seed"),
            composite=self._config.name,
            run_id=self._run_id_str,
            records_extracted=seed_result.records_extracted,
            records_silver=seed_result.records_silver,
        )
        await self._call_save_checkpoint_safe(completed_state, "seed_completed")
        return completed_state

    async def _handle_seed_phase_exception(
        self: _CompositeRunnerStageSupportHostProtocol,
        state: CompositeCheckpointState,
        error: Exception,
    ) -> None:
        """Handle seed-phase failure and persist FAILED checkpoint."""
        log_kwargs: dict[str, object] = {
            "composite": self._config.name,
            "run_id": self._run_id_str,
            "seed_pipeline": self._config.seed.pipeline,
            "error": str(error),
            "error_type": type(error).__name__,
        }
        if isinstance(error, BioETLError):
            log_kwargs["reason_code"] = "unexpected_bioetl_error"
        self._logger.error("Seed pipeline failed", **log_kwargs)
        await self._persist_failed_state(
            state,
            stage="seed_failed",
            error=str(error),
        )

    async def _fail_required_dependencies(
        self: _CompositeRunnerStageSupportHostProtocol,
        state: CompositeCheckpointState,
        required_failed: list[str],
    ) -> None:
        """Persist dependency failure state when required dependencies fail."""
        await self._persist_failed_state(
            state,
            stage="dependencies_failed",
            error=f"Required dependencies failed: {required_failed}",
        )
        raise InvalidStateError(f"Required dependencies failed: {required_failed}")

    @staticmethod
    def _summarize_dependency_outcomes(
        dependency_results: dict[str, DependencyResult],
    ) -> tuple[int, int]:
        """Return counts of successful and failed dependency executions."""
        succeeded = sum(
            1 for result in dependency_results.values() if result.is_success
        )
        failed = len(dependency_results) - succeeded
        return succeeded, failed


__all__ = ["_CompositeRunnerStageSupportMixin"]
