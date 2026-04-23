"""Composite pipeline runner facade.

Coordinates high-level execution flow while delegating stage logic to mixins.
"""

from __future__ import annotations

import warnings
from typing import TYPE_CHECKING

from bioetl.application.composite.lifecycle_observer_service import (
    CompositeLifecycleObserverService,
)
from bioetl.application.composite.runner_pkg.runner_control_plane_mixin import (
    CompositeRunnerControlPlaneMixin,
)
from bioetl.application.composite.runner_pkg.runner_execution_orchestrator import (
    CompositeLockedExecutionContext,
    execute_locked_run_phases,
)
from bioetl.application.composite.runner_pkg.runner_key_flow import (
    CompositeEnrichmentKeyContext,
    extract_enrichment_keys,
)
from bioetl.application.composite.runner_pkg.runner_merge_stage_mixin import (
    CompositeRunnerMergeStageMixin,
)
from bioetl.application.composite.runner_pkg.runner_observability_mixin import (
    CompositeRunnerObservabilityMixin,
)
from bioetl.application.composite.runner_pkg.runner_runtime_helpers import (
    bind_runner_dependencies,
    initialize_runner_runtime_state,
    prepare_run_state,
    resolve_original_run_id,
    run_with_managed_lock,
    validate_runner_can_start,
)
from bioetl.application.composite.runner_pkg.runner_stage_mixin import (
    CompositeRunnerStageMixin,
)
from bioetl.application.composite.runner_pkg.runner_support_mixin import (
    CompositeRunnerSupportMixin,
)
from bioetl.application.composite.runtime_models import (
    CompositeExecutionContext,
    CompositeRunnerDependencies,
    CompositeRuntimeConfig,
)
from bioetl.application.runtime_timestamps import capture_runtime_timing_anchor
from bioetl.domain.composite.result import CompositeResult
from bioetl.domain.composite.state import CompositePipelineState
from bioetl.domain.exceptions import (
    BioETLError,
)
from bioetl.domain.exceptions.pipeline_shutdown import PipelineShutdownError

if TYPE_CHECKING:
    import polars as pl

    from bioetl.application.composite.checkpoint import CompositeCheckpointState
    from bioetl.application.composite.key_extractor import KeyExtractorService
    from bioetl.domain.composite.config import CompositeConfig
    from bioetl.domain.ports import LockPort


__all__ = [
    "CompositePipelineRunner",
    "CompositePipelineRunnerService",
]


class CompositePipelineRunner(
    CompositeRunnerControlPlaneMixin,
    CompositeRunnerSupportMixin,
    CompositeRunnerObservabilityMixin,
    CompositeRunnerStageMixin,
    CompositeRunnerMergeStageMixin,
):
    """Facade/orchestrator for composite pipeline lifecycle."""

    _lock: LockPort
    _key_extractor: KeyExtractorService
    _observer: CompositeLifecycleObserverService

    def __init__(
        self,
        config: CompositeConfig,
        runtime: CompositeRuntimeConfig,
        deps: CompositeRunnerDependencies,
        run_id: str | None = None,
    ) -> None:
        """Initialize composite pipeline orchestrator with injected dependencies.

        Args:
            config: Composite pipeline domain configuration, including seed
                and enricher pipeline names, merge settings, and the
                runtime lock key.
            runtime: Run-time flags such as ``resume``, ``run_type``, and
                ``dry_run`` that control execution behaviour without changing
                domain configuration.
            deps: Grouped collaborator services, ports, and factories.
            run_id: Optional explicit run identifier; a UUID is generated
                automatically when omitted.
        """
        self._config = config
        self._runtime = runtime
        bind_runner_dependencies(self, deps)
        initialize_runner_runtime_state(self, run_id)

    @property
    def run_id(self) -> str:
        """Return current run ID."""
        return self._run_id_str

    def _mark_finished(self, final_state: CompositePipelineState) -> None:
        """Persist terminal runner state for re-entry guards and diagnostics."""
        self._finished = True
        self._final_state = final_state

    @property
    def config(self) -> CompositeConfig:
        """Return composite configuration."""
        return self._config

    def _emit_failed_run(
        self,
        error: Exception,
        *,
        reason_code: str,
        stage: str | None = None,
    ) -> None:
        """Emit the canonical runner failure event through the observer seam."""
        self._observer.emit_run_failed(
            composite_name=self._config.name,
            run_id=self._run_id_str,
            error=error,
            reason_code=reason_code,
            stage=stage,
        )

    def _handle_pipeline_execution_failure(self, error: Exception) -> None:
        """Map execution-phase failures to canonical runner diagnostics."""
        self._mark_finished(CompositePipelineState.FAILED)
        self._record_run_failed(error)
        self._emit_failed_run(
            error,
            reason_code="composite_pipeline_execution_failed",
            stage="run_with_lock",
        )

    def _handle_bioetl_failure(self, error: BioETLError) -> None:
        """Map unexpected BioETL failures to canonical runner diagnostics."""
        self._mark_finished(CompositePipelineState.FAILED)
        self._record_run_failed(error)
        self._emit_failed_run(error, reason_code="unexpected_bioetl_error")

    def _handle_shutdown(self, error: PipelineShutdownError) -> None:
        """Map graceful shutdown to canonical terminal ledger/log semantics."""
        self._mark_finished(CompositePipelineState.FAILED)
        self._record_run_shutdown()
        self._observer.emit_run_shutdown(
            composite_name=self._config.name,
            run_id=self._run_id_str,
            error=error,
            reason=str(error.reason.value),
            reason_code="composite_pipeline_shutdown",
        )

    def _start_run_lifecycle(self) -> None:
        """Validate and log the start of one composite runner execution."""
        self._validate_config_consistency()
        self._run_preflight_validation()
        self._started_at, self._start_time = capture_runtime_timing_anchor(
            clock=self._clock
        )
        self._observer.emit_run_started(
            composite_name=self._config.name,
            run_id=self._run_id_str,
        )
        self._record_run_started()

    async def _run_with_managed_lock(self) -> CompositeResult:
        """Acquire/release the runtime lock around the canonical run body.

        A background :class:`HeartbeatTask` keeps the lock alive for the
        entire duration of the composite pipeline execution, preventing TTL
        expiration for long-running pipelines (>1 hour).
        """
        lock_run_result = await run_with_managed_lock(
            lock_port=self._lock,
            lock_key=self._config.lock_key,
            owner_id=self._run_id,
            lock_ttl_seconds=self._runtime.lock_ttl_seconds,
            heartbeat_interval_seconds=self._runtime.heartbeat_interval_seconds,
            logger=self._logger,
            run_while_locked=self._run_with_lock,
        )
        self._mark_finished(CompositePipelineState.COMPLETED)
        return lock_run_result

    async def run(self) -> CompositeResult:
        """Execute full composite pipeline under runtime lock.

        Returns:
            CompositeResult summarising seed, enrichment, dependency, and merge outcomes.
        """
        validate_runner_can_start(
            finished=self._finished,
            run_id=self._run_id_str,
            final_state=self._final_state,
        )
        self._start_run_lifecycle()

        # Resolve exception group at call-time to avoid stale module-state issues
        # from test-time monkeypatching/reloads.
        from bioetl.application.composite.runner_pkg.runner_constants import (
            PIPELINE_EXECUTION_ERRORS as pipeline_execution_errors,
        )

        try:
            return await self._run_with_managed_lock()
        except PipelineShutdownError as error:
            self._handle_shutdown(error)
            raise
        except pipeline_execution_errors as error:
            self._handle_pipeline_execution_failure(error)
            raise
        except BioETLError as error:
            self._handle_bioetl_failure(error)
            raise

    async def _prepare_run_state(self) -> CompositeCheckpointState:
        """Load checkpoint state and apply resume semantics when configured."""
        state = await prepare_run_state(
            checkpoint_manager=self._checkpoint_manager,
            runtime=self._runtime,
            fsm=self._fsm,
            clock=self._clock,
        )
        self._original_run_id = resolve_original_run_id(
            runtime=self._runtime,
            state=state,
            current_run_id=self._run_id_str,
        )
        return state

    async def _extract_enrichment_keys(self) -> pl.DataFrame:
        """Extract seed keys once the seed phase has completed."""
        enrichment_key_result = await extract_enrichment_keys(
            key_extractor=self._key_extractor,
            logger=self._logger,
            request=CompositeEnrichmentKeyContext(
                composite_name=self._config.name,
                silver_table=self._config.seed.silver_table,
                output_keys=tuple(self._config.seed.output_keys),
            ),
        )
        return enrichment_key_result.keys_df

    async def _execute_locked_run_phases(
        self,
        state: CompositeCheckpointState,
    ) -> tuple[CompositeCheckpointState, CompositeExecutionContext]:
        """Execute composite phases in the canonical lock-held order."""
        locked_phase_result = await execute_locked_run_phases(
            self,
            CompositeLockedExecutionContext(state=state),
        )
        return locked_phase_result.state, locked_phase_result.execution_context

    async def _complete_successful_run(
        self,
        state: CompositeCheckpointState,
        execution_context: CompositeExecutionContext,
    ) -> CompositeResult:
        """Finalize state and emit canonical terminal success artifacts."""
        await self._finalize_pipeline(state)
        completion_context = self._prepare_composite_result_context(execution_context)
        self._log_composite_completion(completion_context)
        result = self._finalize_composite_result(completion_context)
        self._record_run_finished(execution_context)
        return result

    async def _run_with_lock(self) -> CompositeResult:
        """Execute pipeline stages while lock is held."""
        state = await self._prepare_run_state()
        state, execution_context = await self._execute_locked_run_phases(state)
        return await self._complete_successful_run(state, execution_context)


class CompositePipelineRunnerService(CompositePipelineRunner):
    def __init__(self, *args, **kwargs):
        warnings.warn(
            "CompositePipelineRunnerService is deprecated and will be removed in v2.0. "
            "Use CompositePipelineRunner instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        super().__init__(*args, **kwargs)


# Also provide the reverse alias for completeness
CompositePipelineRunnerService_legacy = CompositePipelineRunnerService
